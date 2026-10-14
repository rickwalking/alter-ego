"""The autopilot approves the real image phase and reaches final_review (AE-0365).

Feature: autopilot_runner.feature (AE-0365 scenarios)

Prod 2026-10-14, carousel 8e350d6e: the image phase stored 6 hero images (the
CTA slide uses the owner avatar), the images gate expected ``slides_total``
(7), and every real run revised, regenerated, and escalated there.

This test uses the real ``EditorialWorkflowService``, LangGraph graph,
checkpointer interrupts, run wrapper, the real image phase
(``ensure_slides_from_outline`` + ``run_images``) and a file SQLite database.
Only the LLM artifacts and the image vendor are faked.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from langgraph.checkpoint.memory import MemorySaver
from PIL import Image
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services.carousel import (
    editorial_finalize,
)
from rag_backend.application.services.carousel import (
    editorial_workflow_resume_runner as resume_runner,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    ResumeWorkflowInput,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    build_presentation_review_updates,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.modules.autopilot.constants import (
    GATE_CONTENT,
    GATE_DESIGN,
    GATE_FINAL_REVIEW,
    GATE_IMAGES,
    GATE_OUTLINE,
    REASON_PASSED,
    REASON_READY,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateAction,
    GateSnapshot,
    PolicyDecision,
    ProjectSpec,
    ResumeCommand,
    ResumeStatus,
)
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
    EditorialDriverConfig,
    InProcessEditorialDriver,
)

_OWNER = "autopilot-owner"
_SLIDES = 7
_HERO_IMAGES = 6
_PASSING_SCORE = 90
_MAX_TICKS = 8
_IMAGE_SIZE = (64, 48)
_OUTLINE = [
    {"title": f"Slide {i}", "key_points": ["point"]} for i in range(1, _SLIDES + 1)
]
_LAST_CONTENT = 6
_SCORES = {str(i): {"overall": _PASSING_SCORE} for i in range(_SLIDES)}


def _clean_drafts() -> list[dict[str, object]]:
    """Seven canonical drafts that pass presentation validation."""
    drafts: list[dict[str, object]] = [
        {
            "slide_index": 1,
            "slide_type": "intro",
            "title": "Gancho inicial",
            "draft_text": "Uma promessa curta e concreta para abrir o carrossel.",
        }
    ]
    for index in range(2, _LAST_CONTENT + 1):
        drafts.append({
            "slide_index": index,
            "slide_type": "content",
            "title": f"Insight numero {index}",
            "draft_text": f"Detalhe pratico e verificavel do insight {index}.",
            "content_kind": "features",
            "features": [
                {
                    "icon_name": "target",
                    "title": f"Pratica {index}",
                    "body": "Aplique no proximo ciclo.",
                }
            ],
        })
    drafts.append({
        "slide_index": _SLIDES,
        "slide_type": "cta",
        "title": "Chamada final",
        "draft_text": "Siga o perfil para acompanhar a serie completa.",
    })
    return drafts


class _Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass
class _ImageVendor:
    """Fake image vendor: writes a small real JPEG at the requested path."""

    calls: list[str] = field(default_factory=list)

    async def generate_image(self, prompt: str, output_path: str) -> str:
        del prompt
        self.calls.append(output_path)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", _IMAGE_SIZE, (40, 80, 120)).save(output_path, "JPEG")
        return output_path


async def _fake_artifacts(
    runner: PhaseArtifactRunner,
    state: CarouselWorkflowState,
) -> dict[str, object]:
    """LLM phases are faked; the image phase runs the real pipeline."""
    phase = state.get("current_phase")
    if phase == GATE_OUTLINE:
        return {"outline": list(_OUTLINE)}
    if phase == GATE_CONTENT:
        drafts = _clean_drafts()
        review = build_presentation_review_updates(drafts)
        return {"slide_drafts": drafts, "persona_scores": dict(_SCORES), **review}
    if phase == GATE_DESIGN:
        return {"design_applied": True}
    if phase == GATE_IMAGES:
        return await runner._ensure_image_artifacts(state)
    return {}


@dataclass
class _World:
    session: AsyncSession
    driver: InProcessEditorialDriver
    vendor: _ImageVendor
    project_id: str
    finalized: list[str]


@pytest_asyncio.fixture
async def world(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[_World]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ae0365.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    previous = db_config.c_engine
    db_config.c_engine = engine
    vendor = _ImageVendor()

    async def _finished(project_id: str, reason: str, **_kwargs: object) -> None:
        del project_id, reason

    async def _stage_beat(project_id: str, epoch: int) -> bool:
        # SQLite has no lock_timeout (see the AE-0363 integration test).
        del project_id, epoch
        return True

    finalized: list[str] = []

    async def _finalize(db: AsyncSession, project_id: str) -> None:
        # The slide render needs a headless browser; record the call instead.
        del db
        finalized.append(project_id)

    monkeypatch.setattr(PhaseArtifactRunner, "ensure_for_phase", _fake_artifacts)
    monkeypatch.setattr(resume_runner, "publish_run_finished", _finished)
    monkeypatch.setattr(resume_runner, "write_run_heartbeat_once", _stage_beat)
    monkeypatch.setattr(
        editorial_finalize, "finalize_carousel_after_images_approval", _finalize
    )
    service = EditorialWorkflowService(
        EditorialWorkflowConfig(
            llm=MagicMock(),
            checkpointer=MemorySaver(),
            image_registry=ImageProviderRegistry(vendor, vendor),
        )
    )
    try:
        async with db_config.get_session_maker()() as session:
            driver = _driver(session, service)
            project_id = await _seed_outline_gate(session, service, driver)
            await _set_output_dir(project_id, tmp_path / "carousel")
            yield _World(
                session=session,
                driver=driver,
                vendor=vendor,
                project_id=project_id,
                finalized=finalized,
            )
    finally:
        db_config.c_engine = previous
        await engine.dispose()


def _driver(
    session: AsyncSession,
    service: EditorialWorkflowService,
) -> InProcessEditorialDriver:
    return InProcessEditorialDriver(
        EditorialDriverConfig(
            session=session,
            engine_factory=lambda: service,
            clock=_Clock(),
            stale_after_seconds=180,
        )
    )


async def _seed_outline_gate(
    session: AsyncSession,
    service: EditorialWorkflowService,
    driver: InProcessEditorialDriver,
) -> str:
    """A carousel at the outline gate, the way the runner leaves it."""
    session.add(
        UserModel(
            id=_OWNER,
            email="autopilot@example.com",
            full_name="Autopilot",
            hashed_password="hash",
            role=UserRole.EDITOR.value,
        )
    )
    await session.flush()
    project_id = await driver.create_project(
        ProjectSpec(
            topic="Agents that ship",
            audience="builders",
            niche="ai",
            brief="brief",
            sources=(),
            owner_user_id=_OWNER,
        )
    )
    await service._orchestrator.start(
        project_id,
        {"topic": "Agents that ship"},
        research_findings=[{"content": "finding"}],
    )
    await service.resume_workflow(
        ResumeWorkflowInput(
            project_id=project_id,
            action="approve",
            reviewer_id="",
            db=session,
        )
    )
    await session.commit()
    return project_id


async def _set_output_dir(project_id: str, output_dir: Path) -> None:
    async with db_config.get_session_maker()() as other:
        await other.execute(
            update(CarouselProjectModel)
            .where(CarouselProjectModel.id == project_id)
            .values(output_dir=str(output_dir))
        )
        await other.commit()


async def _tick(world: _World) -> tuple[GateSnapshot, PolicyDecision]:
    """One runner step: read the gate, decide, and approve when it passes."""
    gate = await world.driver.read_gate(world.project_id)
    decision = decide(gate)
    if decision.action is not GateAction.APPROVE:
        return gate, decision
    result = await world.driver.resume(
        ResumeCommand(
            project_id=world.project_id,
            action="approve",
            expected_version=gate.lock_version,
            feedback="",
            phase=gate.phase,
        )
    )
    assert result.status is ResumeStatus.APPLIED
    return gate, decision


async def _drive_to_owner(world: _World) -> list[tuple[GateSnapshot, PolicyDecision]]:
    seen: list[tuple[GateSnapshot, PolicyDecision]] = []
    for _ in range(_MAX_TICKS):
        gate, decision = await _tick(world)
        seen.append((gate, decision))
        if decision.action is not GateAction.APPROVE:
            return seen
    return seen


@pytest.mark.asyncio
async def test_autopilot_approves_real_hero_images_and_reaches_final_review(
    world: _World,
) -> None:
    """Scenario: The autopilot approves the real image phase and reaches
    final_review.
    """
    seen = await _drive_to_owner(world)

    outcomes = [
        (gate.phase, decision.action, decision.reason) for gate, decision in seen
    ]
    assert outcomes == [
        (GATE_OUTLINE, GateAction.APPROVE, REASON_PASSED),
        (GATE_CONTENT, GateAction.APPROVE, REASON_PASSED),
        (GATE_DESIGN, GateAction.APPROVE, REASON_PASSED),
        (GATE_IMAGES, GateAction.APPROVE, REASON_PASSED),
        (GATE_FINAL_REVIEW, GateAction.STOP, REASON_READY),
    ]
    images_gate = seen[3][0]
    assert images_gate.slides_total == _SLIDES
    assert images_gate.hero_images_total == _HERO_IMAGES
    assert len(images_gate.images) == _HERO_IMAGES
    assert all(image.is_jpeg and image.width > 0 for image in images_gate.images)
    written = sorted(Path(path).name for path in world.vendor.calls)
    assert written == sorted(f"slide_{n}.jpg" for n in range(1, _HERO_IMAGES + 1))
    assert world.finalized == [world.project_id]
