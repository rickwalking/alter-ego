"""Scheduled publishing worker (SCHED-001)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.application.services.notification_service import NotificationService
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_BLOG_POST,
    EVENT_SOURCE_SCHEDULER,
    EVENT_TYPE_BLOGPOST_PUBLISHED,
    EVENT_TYPE_BLOGPOST_SCHEDULED,
)
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


class ScheduledPublishService:
    """Publishes blog posts when scheduled_publish_at is reached."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        event_service: WorkflowEventService,
        notification_service: NotificationService,
    ) -> None:
        self._session_factory = session_factory
        self._events = event_service
        self._notifications = notification_service

    async def process_due_posts(self) -> int:
        """Publish all posts whose scheduled time has passed."""
        now = datetime.now(UTC)
        published = 0
        async with self._session_factory() as db:
            result = await db.execute(
                select(BlogPostModel)
                .where(
                    BlogPostModel.status == BlogPostStatus.APPROVED.value,
                    BlogPostModel.scheduled_publish_at.isnot(None),
                    BlogPostModel.scheduled_publish_at <= now,
                )
                .with_for_update()
            )
            posts = list(result.scalars().all())
            for post in posts:
                if post.status != BlogPostStatus.APPROVED.value:
                    continue
                post.status = BlogPostStatus.PUBLISHED.value
                post.published_at = now
                post.scheduled_publish_at = None
                await self._events.emit(
                    db,
                    event_type=EVENT_TYPE_BLOGPOST_PUBLISHED,
                    aggregate_id=str(post.id),
                    aggregate_type=AGGREGATE_TYPE_BLOG_POST,
                    payload={"title": post.title, "scheduled": True},
                    metadata={"source": EVENT_SOURCE_SCHEDULER},
                )
                if post.author_id:
                    await self._notifications.notify_scheduled_published(
                        db,
                        user_id=post.author_id,
                        post_id=str(post.id),
                        title=post.title,
                    )
                published += 1
            if published:
                await db.commit()
                logger.info("scheduled_posts_published", count=published)
        return published

    async def schedule_post(
        self,
        db: AsyncSession,
        post: BlogPostModel,
        scheduled_at: datetime,
    ) -> BlogPostModel:
        """Set scheduled publish time on an approved post."""
        post.scheduled_publish_at = scheduled_at
        await self._events.emit(
            db,
            event_type=EVENT_TYPE_BLOGPOST_SCHEDULED,
            aggregate_id=str(post.id),
            aggregate_type=AGGREGATE_TYPE_BLOG_POST,
            payload={
                "title": post.title,
                "scheduled_publish_at": scheduled_at.isoformat(),
            },
            metadata={"source": EVENT_SOURCE_SCHEDULER},
        )
        await db.flush()
        return post


__all__ = ["ScheduledPublishService"]
