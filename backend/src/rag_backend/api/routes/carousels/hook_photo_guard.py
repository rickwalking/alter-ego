"""``PUT /carousels/{id}/hook-photo`` follows the cover picker's rule for slide 1.

Binding another slide-1 photo changes slide 1 like the cover picker does, so
it follows the same rule: a released carousel is refused with
``cover_switch_requires_review`` (409). On an approved one (scheduled ones
included) the approval is dropped (Pedro's decision, 2026-11-02): in the
commit that stamps the needs-republish marker, before the photo is written,
the carousel goes back to final review, awaiting human, and the entity the
route writes shows it, so the later full-row write keeps it. On a completed
carousel the marker is stamped before the photo is written, so approval is
refused until a render shows the new photo; the approval is read again after
the stamp, so one that landed in between is refused too.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.cover_switch_guard import (
    cover_switch_refusal,
    reopen_refusal,
    reopens_review,
    show_reopened,
)
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_SWITCH_REQUIRES_REVIEW,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.modules.editorial.public import (
    ApprovalReopen,
    CarouselProjectWriteOwner,
    CheckpointReopener,
    EditorialReviewState,
)


def _requires_review() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ERR_COVER_SWITCH_REQUIRES_REVIEW,
    )


async def _reopens(session: AsyncSession, project_id: str) -> bool:
    """409 for a released carousel; True when an approved one is reopened."""
    state = await EditorialReviewState(session).review_state(project_id)
    if state is None:
        return False
    if reopen_refusal(state) is not None:
        raise _requires_review()
    return reopens_review(state)


async def _refuse_if_reviewed(session: AsyncSession, project_id: str) -> None:
    state = await EditorialReviewState(session).review_state(project_id)
    if state is not None and cover_switch_refusal(state) is not None:
        raise _requires_review()


async def prepare_slide_one_change(
    session: AsyncSession, project: CarouselProject, checkpoint: CheckpointReopener
) -> bool:
    """Refuse a released carousel; mark a completed one; reopen an approved one.

    True when the approval was dropped (its Telegram review must be sent again).
    """
    project_id = str(project.id)
    reopen = await _reopens(session, project_id)
    if project.status != CarouselStatus.COMPLETED and not reopen:
        return False
    if project.status == CarouselStatus.COMPLETED:
        await CarouselProjectWriteOwner(session).mark_needs_republish(project_id)
    if reopen:
        await ApprovalReopen(session, checkpoint).reopen(project_id)
        show_reopened(project)
    await session.commit()
    await _refuse_if_reviewed(session, project_id)
    return reopen


__all__ = ["prepare_slide_one_change"]
