"""Fakes for the website cover review switch (selector reads, store, hold)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverPolling,
    AutoCoverSelection,
    AutoCoverSelector,
    AutoCoverWrite,
    CoverBaseline,
    ProjectAtVersion,
)
from rag_backend.application.services.carousel.cover_review_switch import (
    ReviewSwitch,
    ReviewSwitchOutcome,
)
from rag_backend.domain.constants.carousel_autofix import AUTOFIX_STATUS_FIXED
from rag_backend.domain.models import CarouselProject, CarouselStatus

HOOK = uuid4()
ASSET = uuid4()
GENERATION = uuid4()
RUN = uuid4()
BASELINE = CoverBaseline(slide_cover_asset_id=None, hook_asset_id=HOOK)
APPROVED = "approved_for_publish"


def in_review(**changes: object) -> CarouselProject:
    """A completed POV carousel waiting in final review, with ``changes``."""
    project = CarouselProject(topic="Agentes", audience="Devs", niche="IA")
    project.content_mode = "pov"
    project.hook_asset_id = HOOK
    project.status = CarouselStatus.COMPLETED
    project.current_phase = "final_review"
    project.phase_status = "awaiting_human"
    for name, value in changes.items():
        setattr(project, name, value)
    return project


@dataclass
class Reads:
    """The selector's fresh reads: one project and its approval."""

    project: CarouselProject
    workflow_status: str = "draft"
    writes: list[AutoCoverWrite] = field(default_factory=list)

    async def result_asset(self, generation_id: UUID) -> UUID | None:
        assert generation_id == GENERATION
        return ASSET

    async def load(self, project_id: str) -> ProjectAtVersion | None:
        del project_id
        return ProjectAtVersion(
            project=self.project, lock_version=7, workflow_status=self.workflow_status
        )

    async def write(self, command: AutoCoverWrite) -> str:
        self.writes.append(command)
        return AUTOFIX_STATUS_FIXED


@dataclass
class ReviewStore:
    """Records review-switch writes and answers ``outcome`` (or raises)."""

    outcome: ReviewSwitchOutcome = field(
        default_factory=lambda: ReviewSwitchOutcome(status=AUTOFIX_STATUS_FIXED)
    )
    error: Exception | None = None
    writes: list[AutoCoverWrite] = field(default_factory=list)

    async def switch_in_review(self, command: AutoCoverWrite) -> ReviewSwitchOutcome:
        self.writes.append(command)
        if self.error is not None:
            raise self.error
        return self.outcome


@dataclass
class Hold:
    """Records holds and releases; ``run_id`` None means no run to hold."""

    run_id: UUID | None = RUN
    held: list[str] = field(default_factory=list)
    released: list[tuple[UUID, bool]] = field(default_factory=list)
    escalated: list[tuple[UUID, int | None]] = field(default_factory=list)

    async def hold(self, project_id: str) -> UUID | None:
        self.held.append(project_id)
        return self.run_id

    async def release(self, run_id: UUID, *, changed: bool) -> None:
        self.released.append((run_id, changed))

    async def escalate(self, run_id: UUID, version: int | None) -> None:
        self.escalated.append((run_id, version))


class NoReviewHold:
    """No Telegram review to hold."""

    @staticmethod
    async def hold(project_id: str) -> UUID | None:
        del project_id
        return None

    @staticmethod
    async def release(run_id: UUID, *, changed: bool) -> None:
        del run_id, changed

    @staticmethod
    async def escalate(run_id: UUID, version: int | None) -> None:
        del run_id, version


async def no_sleep(seconds: float) -> None:
    del seconds


def selecting(
    reads: Reads, review: ReviewSwitch | None
) -> tuple[AutoCoverSelector, AutoCoverSelection]:
    """The selector over ``reads`` and a selection with ``review``."""
    selection = AutoCoverSelection(
        project_id="p-1", generation_id=GENERATION, baseline=BASELINE, review=review
    )
    polling = AutoCoverPolling(
        interval_seconds=1.0, max_wait_seconds=1.0, sleep=no_sleep
    )
    return AutoCoverSelector(reads, polling), selection


__all__ = [
    "APPROVED",
    "ASSET",
    "BASELINE",
    "GENERATION",
    "HOOK",
    "RUN",
    "Hold",
    "NoReviewHold",
    "Reads",
    "ReviewStore",
    "in_review",
    "no_sleep",
    "selecting",
]
