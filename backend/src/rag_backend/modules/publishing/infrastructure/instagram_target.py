"""Load the carousel row the Instagram publish pre-checks need."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.carousel import (
    CarouselProjectModel,
    CarouselSlideModel,
)
from rag_backend.modules.publishing.domain.instagram_target import (
    InstagramPublishTarget,
)


async def load_instagram_publish_target(
    session: AsyncSession,
    project_id: str,
) -> InstagramPublishTarget | None:
    """Return the target, or None when the carousel does not exist."""
    project = await session.get(CarouselProjectModel, project_id)
    if project is None:
        return None
    numbers = await _slide_numbers(session, project_id)
    caption = project.caption if isinstance(project.caption, str) else ""
    return InstagramPublishTarget(
        workflow_status=str(project.workflow_status),
        status=str(project.status),
        is_public=bool(project.is_public),
        caption=caption,
        slide_numbers=numbers,
    )


async def _slide_numbers(session: AsyncSession, project_id: str) -> tuple[int, ...]:
    result = await session.execute(
        select(CarouselSlideModel.slide_number)
        .where(CarouselSlideModel.project_id == project_id)
        .order_by(CarouselSlideModel.slide_number)
    )
    return tuple(int(number) for number in result.scalars().all())
