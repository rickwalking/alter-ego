"""A carousel waiting at the content (or design) gate for the AE-0392 flow tests.

``seed_gate`` reuses the AE-0367 7-slide v3 carousel (rows + outline) and
writes a content-gate checkpoint whose ``localized_slides`` carry the given
defects, with the presentation report and the fail-closed content-gate report
the engine would have stored for them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.carousel_repair_projection import (
    localized_from_slides,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
    validation_report_to_dict,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_CONTENT
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.domain.gate import (
    GateSnapshot,
    ResearchSourceFact,
    ResumeCommand,
    ResumeResult,
    ResumeStatus,
    SnapshotParts,
)
from rag_backend.modules.autopilot.domain.snapshot import assemble_snapshot
from tests.unit.application.owner_autofix_fixtures_ae0367 import (
    V3,
    _outline,
    rows,
    seed_carousel,
)

BROKEN_HEADING_5 = "a versão para robótica leva o Argon ao mundo físico"
FIXED_HEADING_5 = "A versão para robótica leva o Argon ao mundo físico"
EMOJI_BODY_3 = "O Argon resiste a ataques 🚀 hoje."
FORBIDDEN_PHRASE = "synergy"

Slides = list[dict[str, object]]
Breakage = Callable[[Slides], None]


def _pt(slides: Slides, index: int) -> dict[str, object]:
    return cast(dict[str, object], slides[index - 1]["presentation_pt"])


def _en(slides: Slides, index: int) -> dict[str, object]:
    return cast(dict[str, object], slides[index - 1]["presentation_en"])


def lowercase_heading_5(slides: Slides) -> None:
    _pt(slides, 5)["heading"] = BROKEN_HEADING_5


def empty_slide_4(slides: Slides) -> None:
    for payload in (_pt(slides, 4), _en(slides, 4)):
        payload["body"] = ""
        payload["features"] = []


def emoji_body_3(slides: Slides) -> None:
    _pt(slides, 3)["body"] = EMOJI_BODY_3


def report(slides: Slides) -> dict[str, object]:
    return validation_report_to_dict(
        validate_localized_slides(slides, policy_version=V3)
    )


@dataclass(frozen=True)
class GateSeed:
    """What to break and which gate the checkpoint waits at."""

    breaks: tuple[Breakage, ...] = ()
    phase: str = PHASE_CONTENT
    revisions: int = 0


async def seed_gate(
    engine: EditorialWorkflowService, db: AsyncSession, seed: GateSeed
) -> str:
    """Rows + a gate checkpoint with the seeded defects; returns the project id."""
    project_id = await seed_carousel(db)
    slides = localized_from_slides(await rows(db, project_id))
    for breakage in seed.breaks:
        breakage(slides)
    validation = report(slides)
    content_gate = dict(validation) if validation.get("blocking") is True else {}
    state: dict[str, object] = {
        "project_id": project_id,
        "current_phase": seed.phase,
        "phase_status": "awaiting_human",
        "presentation_policy_version": V3,
        "outline": _outline(),
        "research_findings": [{"title": "Gemini 4 Argon", "summary": ""}],
        "slide_drafts": [dict(slide) for slide in slides],
        "localized_slides": slides,
        "presentation_validation": validation,
        "content_gate_validation": content_gate,
        "revision_count": {seed.phase: seed.revisions},
    }
    graph = engine._orchestrator._engine  # test seeding of a fresh thread only
    await graph.update_state(project_id, state, as_node=seed.phase)
    return project_id


@dataclass
class RealGate:
    """``EditorialDriver`` reading the real checkpoint and row; resume recorded."""

    db: AsyncSession
    engine: EditorialWorkflowService
    resumes: list[ResumeCommand] = field(default_factory=list)
    # The graph has no forbidden-phrase channel: hits are added at this seam.
    forbidden_hits: tuple[str, ...] = ()

    async def read_gate(self, project_id: str) -> GateSnapshot:
        state = await self.engine.get_workflow_state(project_id)
        version = await self.db.scalar(
            select(CarouselProjectModel.lock_version).where(
                CarouselProjectModel.id == project_id
            )
        )
        snapshot = assemble_snapshot(
            SnapshotParts(
                state={
                    **dict(state or {}),
                    "forbidden_phrase_hits": list(self.forbidden_hits),
                },
                images=(),
                slides_total=7,
                lock_version=int(version or 1),
                stale=False,
            )
        )
        return _with_sources(snapshot)

    async def resume(self, command: ResumeCommand) -> ResumeResult:
        self.resumes.append(command)
        return ResumeResult(status=ResumeStatus.APPLIED)


def _with_sources(snapshot: GateSnapshot) -> GateSnapshot:
    from dataclasses import replace

    source = ResearchSourceFact(content="body", summary="", key_points=())
    return replace(snapshot, sources=(source, source, source))
