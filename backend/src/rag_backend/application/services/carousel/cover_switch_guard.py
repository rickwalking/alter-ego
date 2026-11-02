"""Slide 1 of an approved or published carousel never changes.

Changing slide 1 renders the slides again. Doing that on a carousel the owner
already approved (a scheduled one included) would leave it publishable with
an image the owner never saw; on a released carousel the public slides would
change at once. Until the review can be reopened, both are refused: the
picker answers ``cover_switch_requires_review`` and a generated cover stays a
picker option.

Every slide-1 writer that re-renders asks ``cover_switch_refusal`` first, so
the rule is lifted in one place once reopening the review exists.
"""

from __future__ import annotations

from typing import Protocol

from rag_backend.domain.constants.carousel_workflow import (
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.cover_review_switch import (
    REASON_AUTO_SELECT_APPROVED,
    REASON_AUTO_SELECT_PUBLISHED,
)
from rag_backend.domain.models import CarouselProject


class ReviewStateSource(Protocol):
    """The carousel's editorial approval (``workflow_status``)."""

    async def workflow_status(self, project_id: str) -> str:
        """``approved_for_publish`` once approved; empty when unknown."""
        ...


def cover_switch_refusal(project: CarouselProject, workflow_status: str) -> str | None:
    """Why slide 1 must not change without a new approval, if any.

    Released (``is_public``) is published; every Instagram post also needs the
    approval, which nothing drops afterwards.
    """
    if project.is_public:
        return REASON_AUTO_SELECT_PUBLISHED
    if workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH:
        return REASON_AUTO_SELECT_APPROVED
    return None


__all__ = ["ReviewStateSource", "cover_switch_refusal"]
