"""Unit tests for ScheduledPublishService (SCHED-001)."""

# Gherkin: tests/features/phase3_workflow_collaboration.feature
# Scenario: Scheduled post publishes at due time

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.application.services.notification_service import NotificationService
from rag_backend.application.services.scheduled_publish_service import (
    ScheduledPublishService,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.events.memory_event_publisher import (
    MemoryEventPublisher,
    clear_memory_events,
)


@pytest.fixture(autouse=True)
def _clear_events() -> None:
    clear_memory_events()


@pytest.mark.asyncio
async def test_process_due_posts_is_idempotent(test_engine) -> None:
    """Processing due posts twice should only publish once."""
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as db:
        post = BlogPostModel(
            id="scheduled-post-1",
            title="Scheduled Post",
            slug="scheduled-post-worker",
            status=BlogPostStatus.APPROVED.value,
            content={"body": "hello"},
            scheduled_publish_at=datetime.now(UTC) - timedelta(minutes=5),
            author_id=None,
        )
        db.add(post)
        await db.commit()

    service = ScheduledPublishService(
        session_factory,
        WorkflowEventService(MemoryEventPublisher()),
        NotificationService(),
    )

    first = await service.process_due_posts()
    second = await service.process_due_posts()

    assert first == 1
    assert second == 0

    async with session_factory() as db:
        updated = await db.get(BlogPostModel, "scheduled-post-1")
        assert updated is not None
        assert updated.status == BlogPostStatus.PUBLISHED.value
        assert updated.scheduled_publish_at is None
