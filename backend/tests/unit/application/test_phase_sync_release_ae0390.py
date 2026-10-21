"""The phase sync commits before anything else runs on the row (AE-0390).

Gherkin: tests/features/workflow_tracing_and_heartbeat.feature
  Scenario: The phase sync releases the project row before finalize, events and beats

The flushed phase-sync UPDATE holds the ``carousel_projects`` row lock until
commit. Committing it at once releases the row for the run heartbeat; the
real two-session proof is tests/integration/test_run_heartbeat_lock_pg.py.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.application.services.carousel import (
    editorial_workflow_service as workflow_service,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    ResumeWorkflowInput,
)

_PROJECT = "11111111-1111-1111-1111-111111111111"
_OUTLINE_GATE = {"current_phase": "outline", "phase_status": "awaiting_human"}


class _Owner:
    """Records the write-owner calls the service makes, in order."""

    order: ClassVar[list[str]] = []

    def __init__(self, _session: object) -> None:
        pass

    async def sync_phase(self, _project_id: str, _state: object) -> None:
        self.order.append("sync")

    async def commit(self) -> None:
        self.order.append("commit")


@pytest.fixture
def order(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    calls: list[str] = []
    _Owner.order = calls

    async def _emit(_request: object) -> None:
        calls.append("review_events")

    async def _sse(_project_id: str, _state: object) -> None:
        calls.append("sse")

    monkeypatch.setattr(workflow_service, "CarouselProjectWriteOwner", _Owner)
    monkeypatch.setattr(workflow_service, "emit_review_event", _emit)
    monkeypatch.setattr(workflow_service, "publish_workflow_sse_updates", _sse)
    monkeypatch.setattr(workflow_service, "persist_edited_slide_copy", AsyncMock())
    monkeypatch.setattr(workflow_service, "record_human_review", lambda **_: None)
    yield calls


def _service() -> EditorialWorkflowService:
    service = EditorialWorkflowService(EditorialWorkflowConfig(llm=MagicMock()))
    orchestrator = MagicMock()
    orchestrator.get_state = AsyncMock(
        side_effect=[{"current_phase": "research"}, dict(_OUTLINE_GATE)]
    )
    orchestrator.resume = AsyncMock(return_value=dict(_OUTLINE_GATE))
    orchestrator.continue_pending = AsyncMock(return_value=dict(_OUTLINE_GATE))
    service._orchestrator = orchestrator
    return service


def _approve(db: object) -> ResumeWorkflowInput:
    return ResumeWorkflowInput(
        project_id=_PROJECT, action="approve", reviewer_id="", db=db
    )


@pytest.mark.asyncio
async def test_resume_commits_the_sync_before_events_and_sse(order: list[str]) -> None:
    await _service().resume_workflow(_approve(MagicMock()))

    assert order == ["sync", "commit", "review_events", "sse"]


@pytest.mark.asyncio
async def test_redrive_commits_the_sync_before_sse(order: list[str]) -> None:
    service = _service()
    service._orchestrator.get_state = AsyncMock(return_value=dict(_OUTLINE_GATE))

    await service.redrive_pending_phase(_PROJECT, MagicMock())

    assert order == ["sync", "commit", "sse"]


@pytest.mark.asyncio
async def test_no_session_means_no_sync_and_no_commit(order: list[str]) -> None:
    await _service().resume_workflow(_approve(None))

    assert order == ["review_events", "sse"]
