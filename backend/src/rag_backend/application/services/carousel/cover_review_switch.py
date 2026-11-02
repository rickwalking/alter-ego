"""Switch slide 1 of a completed carousel that waits in final review.

Pedro's decision (2026-11-02): a cover the owner generates from the website on
a completed carousel still waiting for its first approval becomes slide 1.
The slides are rendered again and the carousel stays in final review, so the
owner approves the new render before anything goes out. Nothing is published
and the approval is never touched.

- Only ``final_review`` / ``awaiting_human`` qualifies; an approved (scheduled
  included) or published carousel is refused by ``cover_switch_refusal`` and
  the cover stays a picker option.
- The owner's choice while the job ran wins (any change to the cover fields
  since the baseline). A cover chosen before the job does not block the
  switch: the owner asked for a new cover on a finished carousel.
- Before the write the review is held (``ReviewHold``): an autopilot run in
  ``awaiting_owner`` leaves it, so its Telegram review cannot approve the new
  render, and is released afterwards, with ``changed`` when the slides moved
  (the worker then sends the review again at the new lock version).
- A lock-version conflict is a logged skip; a replay is ``already_selected``.
- A failed render, or an approval that landed between the write and the
  render, rolls the cover back (``rolled_back``, the review sent again).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverSelection,
    AutoCoverWrite,
    CoverBaseline,
    ProjectAtVersion,
    cover_baseline,
)
from rag_backend.application.services.carousel.cover_switch_guard import (
    cover_switch_refusal,
    review_state_of,
)
from rag_backend.domain.constants.carousel_autofix import AUTOFIX_STATUS_FIXED
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_FINAL_REVIEW,
    PHASE_STATUS_AWAITING_HUMAN,
)
from rag_backend.domain.constants.cover_autoselect import (
    OUTCOME_AUTO_SELECT_ALREADY,
    OUTCOME_AUTO_SELECT_SELECTED,
    REASON_AUTO_SELECT_MANUAL_CHOICE,
)
from rag_backend.domain.constants.cover_review_switch import (
    REASON_AUTO_SELECT_NOT_IN_REVIEW,
    REASON_AUTO_SELECT_ROLLED_BACK,
)
from rag_backend.domain.models import CarouselProject

_MOVED = frozenset({AUTOFIX_STATUS_FIXED, REASON_AUTO_SELECT_ROLLED_BACK})


@dataclass(frozen=True, kw_only=True)
class ReviewSwitchOutcome:
    """``AUTOFIX_STATUS_*`` or a ``REASON_*`` refusal, and the render errors."""

    status: str
    render_errors: tuple[str, ...] = ()


class ReviewCoverStore(Protocol):
    """Re-check, store under the CAS and re-render (one fresh session)."""

    async def switch_in_review(self, command: AutoCoverWrite) -> ReviewSwitchOutcome:
        """The outcome; nothing is written on a refusal or a conflict."""
        ...


class ReviewHold(Protocol):
    """Takes the Telegram review out of the owner's hands while slide 1 changes."""

    async def hold(self, project_id: str) -> UUID | None:
        """The held run, or None when no run waits for the owner's review."""
        ...

    async def release(self, run_id: UUID, *, changed: bool) -> None:
        """Hand the run back; ``changed`` sends the review again."""
        ...


@dataclass(frozen=True, kw_only=True)
class ReviewSwitch:
    """The store and the review hold of a website generation."""

    store: ReviewCoverStore
    hold: ReviewHold


def review_refusal(found: ProjectAtVersion) -> str | None:
    """Approved, published, or not waiting in final review."""
    guard = cover_switch_refusal(review_state_of(found.project, found.workflow_status))
    if guard is not None:
        return guard
    project = found.project
    if project.current_phase != PHASE_FINAL_REVIEW:
        return REASON_AUTO_SELECT_NOT_IN_REVIEW
    if project.phase_status != PHASE_STATUS_AWAITING_HUMAN:
        return REASON_AUTO_SELECT_NOT_IN_REVIEW
    return None


def review_choice_refusal(
    project: CarouselProject, baseline: CoverBaseline, asset_id: UUID
) -> str | None:
    """Already the cover, or the owner changed slide 1 since the baseline."""
    cover = project.slide_cover
    if cover is not None and cover.asset_id == asset_id:
        return OUTCOME_AUTO_SELECT_ALREADY
    if cover_baseline(project) != baseline:
        return REASON_AUTO_SELECT_MANUAL_CHOICE
    return None


async def switch_in_review(
    selection: AutoCoverSelection, target: tuple[ProjectAtVersion, UUID]
) -> str:
    """``selected`` / ``already_selected``, or the refusal (logged by the caller)."""
    found, asset_id = target
    review = selection.review
    if review is None:
        return REASON_AUTO_SELECT_NOT_IN_REVIEW
    refusal = review_refusal(found) or review_choice_refusal(
        found.project, selection.baseline, asset_id
    )
    if refusal is not None:
        return refusal
    write = AutoCoverWrite(
        project_id=selection.project_id,
        asset_id=asset_id,
        expected_version=found.lock_version,
        baseline=selection.baseline,
    )
    outcome = await _held_switch(review, write)
    if outcome.status != AUTOFIX_STATUS_FIXED:
        return outcome.status
    return OUTCOME_AUTO_SELECT_SELECTED


async def _held_switch(
    review: ReviewSwitch, write: AutoCoverWrite
) -> ReviewSwitchOutcome:
    """Hold the review, switch, release; an error releases as changed (safe)."""
    run_id = await review.hold.hold(write.project_id)
    changed = True
    try:
        outcome = await review.store.switch_in_review(write)
        changed = outcome.status in _MOVED
    finally:
        if run_id is not None:
            await review.hold.release(run_id, changed=changed)
    return outcome


__all__ = [
    "ReviewCoverStore",
    "ReviewHold",
    "ReviewSwitch",
    "ReviewSwitchOutcome",
    "review_choice_refusal",
    "review_refusal",
    "switch_in_review",
]
