"""Unit tests for NotificationService (NOTIF-001, NOTIF-002)."""

# Gherkin: tests/features/phase3_workflow_collaboration.feature
# Scenario: Review request notification
# Scenario: Deadline reminder deduplication

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.notification_service import NotificationService
from rag_backend.domain.constants.notifications import (
    NOTIFICATION_STATUS_UNREAD,
    NOTIFICATION_TYPE_DEADLINE_REMINDER,
    NOTIFICATION_TYPE_REVIEW_REQUEST,
)
from rag_backend.domain.constants.workflow_validation import (
    CONTENT_TYPE_BLOG_POST,
    METADATA_KEY_REMINDER_SENT,
)
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.models.notification import NotificationModel
from rag_backend.infrastructure.database.models.user import UserModel


@pytest.mark.asyncio
async def test_create_review_request_sets_email_sent_when_user_exists(
    db_session: AsyncSession,
) -> None:
    """Review request should mark email_sent when recipient exists."""
    reviewer = UserModel(
        id="reviewer-1",
        email="reviewer@example.com",
        full_name="Reviewer",
        hashed_password="hash",
        role=UserRole.EDITOR.value,
    )
    db_session.add(reviewer)
    await db_session.flush()

    service = NotificationService()
    notification = await service.create_review_request(
        db_session,
        user_id=reviewer.id,
        content_id="post-1",
        content_type=CONTENT_TYPE_BLOG_POST,
        title="Test Post",
    )
    await db_session.commit()

    assert notification.email_sent is True
    assert notification.notification_type == NOTIFICATION_TYPE_REVIEW_REQUEST


@pytest.mark.asyncio
async def test_create_review_request_email_not_sent_for_missing_user(
    db_session: AsyncSession,
) -> None:
    """Review request should not claim email sent when user is missing."""
    service = NotificationService()
    notification = await service.create_review_request(
        db_session,
        user_id="missing-user",
        content_id="post-1",
        content_type=CONTENT_TYPE_BLOG_POST,
        title="Test Post",
    )

    assert notification.email_sent is False


@pytest.mark.asyncio
async def test_send_deadline_reminders_deduplicates(db_session: AsyncSession) -> None:
    """Deadline reminders should only fire once per overdue review request."""
    user = UserModel(
        id="reviewer-2",
        email="reviewer2@example.com",
        full_name="Reviewer Two",
        hashed_password="hash",
        role=UserRole.EDITOR.value,
    )
    db_session.add(user)
    overdue = NotificationModel(
        user_id=user.id,
        notification_type=NOTIFICATION_TYPE_REVIEW_REQUEST,
        title="Review: Overdue Post",
        body="Please review",
        status=NOTIFICATION_STATUS_UNREAD,
        content_id="post-2",
        content_type=CONTENT_TYPE_BLOG_POST,
        deadline_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(overdue)
    await db_session.flush()

    service = NotificationService()
    first = await service.send_deadline_reminders(db_session)
    await db_session.refresh(overdue)
    second = await service.send_deadline_reminders(db_session)

    assert first == 1
    assert second == 0
    assert overdue.metadata_json.get(METADATA_KEY_REMINDER_SENT) is True

    from sqlalchemy import select

    result = await db_session.execute(
        select(NotificationModel).where(
            NotificationModel.notification_type == NOTIFICATION_TYPE_DEADLINE_REMINDER,
        )
    )
    assert len(list(result.scalars().all())) == 1
