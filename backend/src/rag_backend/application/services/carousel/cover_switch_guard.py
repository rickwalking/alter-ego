"""Slide 1 of a published carousel never changes; an approved one is reopened.

Changing slide 1 renders the slides again. On a released carousel the public
slides would change at once, so it is refused: the picker answers
``cover_switch_requires_review`` and a generated cover stays a picker option.

Pedro's decision (2026-11-02): on an approved carousel (a scheduled one
included) the switch drops the approval instead, in the same transaction as
the slide-1 write (``ReviewReopener``): the carousel is back in final review,
awaiting human, and only a fresh approve restores the approval, so nothing
publishes an image the owner never saw. ``reopen_refusal`` and
``reopens_review`` are asked before and again under the project lock by
every slide-1 writer. ``cover_switch_refusal`` (approved or released) is the
render guard's rule: a render never changes slide 1 of an approved carousel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_FINAL_REVIEW,
    PHASE_STATUS_AWAITING_HUMAN,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.cover_review_switch import (
    REASON_AUTO_SELECT_APPROVED,
    REASON_AUTO_SELECT_PUBLISHED,
)
from rag_backend.domain.models import CarouselProject


@dataclass(frozen=True, kw_only=True)
class ReviewState:
    """The carousel's editorial approval and release, as committed now."""

    workflow_status: str
    is_public: bool


class ReviewStateSource(Protocol):
    """A fresh read of the approval and release (never a cached row)."""

    async def review_state(self, project_id: str) -> ReviewState | None:
        """The committed state; None for an unknown carousel."""
        ...


def review_state_of(project: CarouselProject, workflow_status: str) -> ReviewState:
    """``project``'s release with ``workflow_status``."""
    return ReviewState(workflow_status=workflow_status, is_public=project.is_public)


def cover_switch_refusal(state: ReviewState) -> str | None:
    """Why a render must not change slide 1 (the render guard), if any.

    Released (``is_public``) is published; an approved carousel keeps the
    slide 1 it was approved with until a switch drops the approval.
    """
    if state.is_public:
        return REASON_AUTO_SELECT_PUBLISHED
    if state.workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH:
        return REASON_AUTO_SELECT_APPROVED
    return None


def reopen_refusal(state: ReviewState) -> str | None:
    """Why slide 1 must not change at all: only a released carousel."""
    if state.is_public:
        return REASON_AUTO_SELECT_PUBLISHED
    return None


def reopens_review(state: ReviewState) -> bool:
    """True when a slide-1 change must drop the approval (approved, not public)."""
    return (
        not state.is_public
        and state.workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
    )


class ReopenRefusedError(Exception):
    """The reopen found the row released, no longer approved, or a checkpoint
    that cannot wait at the final review: nothing may be written."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ReviewReopener(Protocol):
    """Drops the approval of a carousel whose slide 1 is changing."""

    async def reopen(self, project_id: str) -> None:
        """Under the row lock, re-check that the carousel is still approved and
        not released; the checkpoint waits at the final review again; then the
        row is a draft at ``final_review / awaiting_human`` (flush; the caller
        commits with the slide-1 write). Raises ``ReopenRefusedError`` before
        anything is written otherwise."""
        ...


def show_reopened(project: CarouselProject) -> None:
    """Put the reopened review on the entity a later full-row write uses."""
    project.current_phase = PHASE_FINAL_REVIEW
    project.phase_status = PHASE_STATUS_AWAITING_HUMAN


__all__ = [
    "ReopenRefusedError",
    "ReviewReopener",
    "ReviewState",
    "ReviewStateSource",
    "cover_switch_refusal",
    "reopen_refusal",
    "reopens_review",
    "review_state_of",
    "show_reopened",
]
