"""SQL read of the owner's recent slide-1 openings (the RecentHookReader port).

Two queries over the owner's carousels: the newest non-blank slide-1 headings
(the given project excluded, capped) and their total count, which seeds the
hook rotation. An unknown or ownerless project yields the empty result.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.protocols.recent_hooks import (
    RecentHookQuery,
    RecentHooks,
)
from rag_backend.infrastructure.database.models.carousel import (
    CarouselProjectModel,
    CarouselSlideModel,
)

_HOOK_SLIDE_NUMBER = 1


class SqlRecentHookReader:
    """``RecentHookReader`` on the request's session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def recent_hooks(self, query: RecentHookQuery) -> RecentHooks:
        owner = (
            select(CarouselProjectModel.owner_id)
            .where(CarouselProjectModel.id == query.project_id)
            .scalar_subquery()
        )
        base = (
            select(CarouselSlideModel.heading)
            .join(
                CarouselProjectModel,
                CarouselProjectModel.id == CarouselSlideModel.project_id,
            )
            .where(CarouselSlideModel.slide_number == _HOOK_SLIDE_NUMBER)
            .where(CarouselProjectModel.owner_id == owner)
            .where(CarouselProjectModel.id != query.project_id)
            .where(func.trim(CarouselSlideModel.heading) != "")
        )
        headings_rows = await self._session.execute(
            base.order_by(CarouselSlideModel.created_at.desc()).limit(query.limit)
        )
        total_rows = await self._session.execute(
            select(func.count()).select_from(base.subquery())
        )
        headings = tuple(
            heading.strip()
            for heading in headings_rows.scalars()
            if isinstance(heading, str) and heading.strip()
        )
        return RecentHooks(headings=headings, total=int(total_rows.scalar_one()))


__all__ = ["SqlRecentHookReader"]
