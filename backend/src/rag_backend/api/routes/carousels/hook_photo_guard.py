"""``PUT /carousels/{id}/hook-photo`` never changes slide 1 of an approved carousel.

Binding another slide-1 photo changes slide 1 like the cover picker does, so
it follows the same rule: an approved (scheduled ones included) or released
carousel is refused with ``cover_switch_requires_review`` (409). On a completed
carousel the needs-republish marker is stamped before the photo is written, so
approval is refused until a render shows the new photo; the approval is read
again after the stamp, so one that landed in between is refused too.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.cover_switch_guard import (
    cover_switch_refusal,
)
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_SWITCH_REQUIRES_REVIEW,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.modules.editorial.public import (
    CarouselProjectWriteOwner,
    EditorialReviewState,
)


async def _refuse_if_reviewed(session: AsyncSession, project_id: str) -> None:
    state = await EditorialReviewState(session).review_state(project_id)
    if state is not None and cover_switch_refusal(state) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_COVER_SWITCH_REQUIRES_REVIEW,
        )


async def prepare_slide_one_change(
    session: AsyncSession, project: CarouselProject
) -> None:
    """Refuse an approved or released carousel; mark a completed one for render."""
    project_id = str(project.id)
    await _refuse_if_reviewed(session, project_id)
    if project.status != CarouselStatus.COMPLETED:
        return
    await CarouselProjectWriteOwner(session).mark_needs_republish(project_id)
    await session.commit()
    await _refuse_if_reviewed(session, project_id)


__all__ = ["prepare_slide_one_change"]
