"""Content calendar aggregation (SCHED-002)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel


class ContentCalendarService:
    """Builds calendar entries from scheduled and published content."""

    async def get_calendar(
        self,
        db: AsyncSession,
        *,
        start: datetime,
        end: datetime,
        author_id: str | None = None,
    ) -> list[dict[str, object]]:
        """Return calendar items in the date range."""
        items: list[dict[str, object]] = []
        blog_query = select(BlogPostModel).where(
            or_(
                BlogPostModel.scheduled_publish_at.between(start, end),
                BlogPostModel.published_at.between(start, end),
            )
        )
        if author_id:
            blog_query = blog_query.where(BlogPostModel.author_id == author_id)
        blog_result = await db.execute(blog_query)
        for post in blog_result.scalars().all():
            event_date = post.scheduled_publish_at or post.published_at
            if event_date is None:
                continue
            items.append(
                {
                    "id": str(post.id),
                    "content_type": "blog_post",
                    "title": post.title,
                    "status": post.status,
                    "event_date": event_date.isoformat(),
                    "is_scheduled": post.scheduled_publish_at is not None,
                }
            )

        carousel_query = select(CarouselProjectModel).where(
            CarouselProjectModel.updated_at.between(start, end)
        )
        if author_id:
            carousel_query = carousel_query.where(CarouselProjectModel.owner_id == author_id)
        carousel_result = await db.execute(carousel_query)
        for project in carousel_result.scalars().all():
            items.append(
                {
                    "id": str(project.id),
                    "content_type": "carousel",
                    "title": project.title or project.topic,
                    "status": project.status,
                    "event_date": project.updated_at.isoformat()
                    if project.updated_at
                    else datetime.now(UTC).isoformat(),
                    "phase": project.current_phase,
                    "phase_status": project.phase_status,
                }
            )
        items.sort(key=lambda item: str(item.get("event_date", "")))
        return items


__all__ = ["ContentCalendarService"]
