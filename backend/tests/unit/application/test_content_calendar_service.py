"""Unit tests for ContentCalendarService (SCHED-002)."""

# Gherkin: tests/features/phase3_workflow_collaboration.feature
# Scenario: View calendar entries

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.content_calendar_service import ContentCalendarService
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel


@pytest.mark.asyncio
async def test_get_calendar_includes_scheduled_post(db_session: AsyncSession) -> None:
    scheduled_at = datetime.now(UTC) + timedelta(days=3)
    post = BlogPostModel(
        title="Scheduled Post",
        slug="scheduled-post",
        status=BlogPostStatus.APPROVED.value,
        scheduled_publish_at=scheduled_at,
    )
    db_session.add(post)
    await db_session.commit()

    service = ContentCalendarService()
    items = await service.get_calendar(
        db_session,
        start=datetime.now(UTC) - timedelta(days=1),
        end=datetime.now(UTC) + timedelta(days=10),
    )
    assert any(item["id"] == str(post.id) for item in items)
