"""In-process workflow start through the real editorial service (AE-0354).

The orchestrator stands in for the LLM and image providers. The runner
adapter calls the service directly, with no HTTP client.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.domain.constants.carousel import CAROUSEL_DEFAULT_SLIDES_CONFIG
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.modules.autopilot.constants import (
    AGENT_NAME_AUTOPILOT,
    CONTENT_TYPE_CAROUSEL,
    GATE_RESEARCH,
    LANGFUSE_FIELD_AGENT_NAME,
    LANGFUSE_FIELD_CONTENT_TYPE,
    LANGFUSE_FIELD_PHASE,
    LANGFUSE_FIELD_PROJECT_ID,
    LANGUAGE_PT_BR,
    PHASE_STATUS_AWAITING,
)
from rag_backend.modules.autopilot.domain.gate import ProjectSpec, StartCommand
from rag_backend.modules.autopilot.infrastructure import editorial_driver
from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
    EditorialDriverConfig,
    InProcessEditorialDriver,
)

_OWNER = "autopilot-owner"
_STATE: dict[str, object] = {
    "current_phase": GATE_RESEARCH,
    "phase_status": PHASE_STATUS_AWAITING,
}


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 10, 13, tzinfo=UTC)


def _engine() -> EditorialWorkflowService:
    service = EditorialWorkflowService(EditorialWorkflowConfig(llm=MagicMock()))
    orchestrator = MagicMock()
    orchestrator.get_state = AsyncMock(side_effect=[None, dict(_STATE)])
    orchestrator.enrich_research_sources = AsyncMock(return_value=[])
    orchestrator.synthesize_research = AsyncMock(return_value=[{"content": "finding"}])
    orchestrator.start = AsyncMock(return_value=dict(_STATE))
    service._orchestrator = orchestrator
    return service


@pytest.mark.asyncio
async def test_start_uses_the_editorial_service_in_process(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Start creates a pt-BR carousel and never assigns a reviewer."""
    db_session.add(
        UserModel(
            id=_OWNER,
            email="autopilot@example.com",
            full_name="Autopilot",
            hashed_password="hash",
            role=UserRole.EDITOR.value,
        )
    )
    await db_session.flush()
    captured: list[dict[str, str]] = []

    @contextmanager
    def _spy(
        metadata: dict[str, str],
        callbacks: list[object] | None = None,
    ) -> Iterator[None]:
        captured.append(dict(metadata))
        yield

    monkeypatch.setattr(editorial_driver, "propagate_attributes", _spy)
    service = _engine()
    driver = InProcessEditorialDriver(
        EditorialDriverConfig(
            session=db_session,
            engine_factory=lambda: service,
            clock=_Clock(),
            stale_after_seconds=180,
        )
    )
    spec = ProjectSpec(
        topic="Agents that ship",
        audience="builders",
        niche="ai",
        brief="A short brief.",
        sources=("https://example.com/story",),
        owner_user_id=_OWNER,
    )
    project_id = await driver.create_project(spec)
    status = await driver.start(
        StartCommand(project_id=project_id, spec=spec, phase=GATE_RESEARCH)
    )

    row = await db_session.get(CarouselProjectModel, project_id)
    assert status is editorial_driver.StartStatus.STARTED
    assert row is not None
    assert row.language == LANGUAGE_PT_BR
    assert row.generate_images == 1
    assert row.slides_config == CAROUSEL_DEFAULT_SLIDES_CONFIG
    assert row.owner_id == _OWNER
    assert row.assigned_reviewer_id is None
    assert row.current_phase == GATE_RESEARCH
    assert captured == [
        {
            LANGFUSE_FIELD_CONTENT_TYPE: CONTENT_TYPE_CAROUSEL,
            LANGFUSE_FIELD_AGENT_NAME: AGENT_NAME_AUTOPILOT,
            LANGFUSE_FIELD_PHASE: GATE_RESEARCH,
            LANGFUSE_FIELD_PROJECT_ID: project_id,
        }
    ]
    assert service._orchestrator.synthesize_research.await_count == 1
    assert service._orchestrator.start.await_count == 1
