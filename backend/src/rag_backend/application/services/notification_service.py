"""Notification service for in-app and email alerts (NOTIF-001)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.notifications import (
    EMAIL_SUBJECT_DEADLINE_REMINDER,
    EMAIL_SUBJECT_REVIEW_REQUEST,
    EMAIL_SUBJECT_REVISION_CAP_ESCALATION,
    EMAIL_SUBJECT_SCHEDULED_PUBLISHED,
    NOTIFICATION_BODY_REVISION_CAP_ESCALATION,
    NOTIFICATION_CHANNEL_EMAIL,
    NOTIFICATION_CHANNEL_IN_APP,
    NOTIFICATION_STATUS_READ,
    NOTIFICATION_STATUS_UNREAD,
    NOTIFICATION_TYPE_DEADLINE_REMINDER,
    NOTIFICATION_TYPE_REVIEW_REQUEST,
    NOTIFICATION_TYPE_REVISION_CAP_ESCALATION,
    NOTIFICATION_TYPE_SCHEDULED_PUBLISHED,
)
from rag_backend.domain.constants.workflow_validation import (
    CONTENT_TYPE_BLOG_POST,
    METADATA_KEY_ORIGINAL_NOTIFICATION_ID,
    METADATA_KEY_REMINDER_SENT,
    NOTIFICATION_BODY_DEADLINE_REMINDER,
    NOTIFICATION_BODY_REVIEW_REQUEST,
    NOTIFICATION_BODY_SCHEDULED_PUBLISHED,
)
from rag_backend.infrastructure.database.models.notification import NotificationModel
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


class NotificationService:
    """Creates and delivers in-app notifications with optional email."""

    async def create_review_request(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        content_id: str,
        content_type: str,
        title: str,
        deadline_hours: int = 24,
    ) -> NotificationModel:
        """Notify a reviewer that content awaits their review."""
        deadline = datetime.now(UTC) + timedelta(hours=deadline_hours)
        body = NOTIFICATION_BODY_REVIEW_REQUEST.format(content_type=content_type)
        notification = NotificationModel(
            user_id=user_id,
            notification_type=NOTIFICATION_TYPE_REVIEW_REQUEST,
            title=EMAIL_SUBJECT_REVIEW_REQUEST.format(title=title),
            body=body,
            status=NOTIFICATION_STATUS_UNREAD,
            content_id=content_id,
            content_type=content_type,
            metadata_json={
                "channels": [NOTIFICATION_CHANNEL_IN_APP, NOTIFICATION_CHANNEL_EMAIL]
            },
            deadline_at=deadline,
        )
        db.add(notification)
        await db.flush()
        notification.email_sent = await self._send_email(
            db,
            user_id,
            EMAIL_SUBJECT_REVIEW_REQUEST.format(title=title),
            body,
        )
        return notification

    async def create_revision_cap_escalation(
        self,
        db: AsyncSession,
        *,
        content_id: str,
        content_type: str,
        phase: str,
        title: str,
    ) -> list[NotificationModel]:
        """Notify all admins when a workflow phase exceeds the revision cap."""
        from rag_backend.domain.models import UserRole
        from rag_backend.infrastructure.database.models.user import UserModel

        result = await db.execute(
            select(UserModel).where(UserModel.role == UserRole.ADMIN.value)
        )
        admins = list(result.scalars().all())
        body = NOTIFICATION_BODY_REVISION_CAP_ESCALATION.format(
            content_id=content_id,
            phase=phase,
        )
        subject = EMAIL_SUBJECT_REVISION_CAP_ESCALATION.format(title=title)
        notifications: list[NotificationModel] = []
        for admin in admins:
            notification = NotificationModel(
                user_id=str(admin.id),
                notification_type=NOTIFICATION_TYPE_REVISION_CAP_ESCALATION,
                title=subject,
                body=body,
                status=NOTIFICATION_STATUS_UNREAD,
                content_id=content_id,
                content_type=content_type,
                metadata_json={
                    "phase": phase,
                    "channels": [NOTIFICATION_CHANNEL_IN_APP],
                },
            )
            db.add(notification)
            notifications.append(notification)
        if notifications:
            await db.flush()
        return notifications

    async def list_for_user(
        self,
        db: AsyncSession,
        user_id: str,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[NotificationModel]:
        """List notifications for a user."""
        query = select(NotificationModel).where(NotificationModel.user_id == user_id)
        if unread_only:
            query = query.where(NotificationModel.status == NOTIFICATION_STATUS_UNREAD)
        query = query.order_by(NotificationModel.created_at.desc()).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def mark_read(
        self,
        db: AsyncSession,
        notification_id: str,
        user_id: str,
    ) -> NotificationModel | None:
        """Mark a notification as read."""
        notification = await db.get(NotificationModel, notification_id)
        if notification is None or notification.user_id != user_id:
            return None
        notification.status = NOTIFICATION_STATUS_READ
        notification.read_at = datetime.now(UTC)
        await db.flush()
        return notification

    async def send_deadline_reminders(self, db: AsyncSession) -> int:
        """Send reminders for overdue review notifications (NOTIF-002)."""
        now = datetime.now(UTC)
        result = await db.execute(
            select(NotificationModel).where(
                NotificationModel.notification_type == NOTIFICATION_TYPE_REVIEW_REQUEST,
                NotificationModel.status == NOTIFICATION_STATUS_UNREAD,
                NotificationModel.deadline_at.isnot(None),
                NotificationModel.deadline_at <= now,
            )
        )
        pending = list(result.scalars().all())
        sent = 0
        for item in pending:
            metadata = (
                item.metadata_json if isinstance(item.metadata_json, dict) else {}
            )
            if metadata.get(METADATA_KEY_REMINDER_SENT):
                continue
            reminder = NotificationModel(
                user_id=item.user_id,
                notification_type=NOTIFICATION_TYPE_DEADLINE_REMINDER,
                title=EMAIL_SUBJECT_DEADLINE_REMINDER.format(title=item.title),
                body=NOTIFICATION_BODY_DEADLINE_REMINDER,
                status=NOTIFICATION_STATUS_UNREAD,
                content_id=item.content_id,
                content_type=item.content_type,
                metadata_json={METADATA_KEY_ORIGINAL_NOTIFICATION_ID: item.id},
            )
            db.add(reminder)
            await self._send_email(
                db,
                item.user_id,
                EMAIL_SUBJECT_DEADLINE_REMINDER.format(title=item.title),
                NOTIFICATION_BODY_DEADLINE_REMINDER,
            )
            item.metadata_json = {**metadata, METADATA_KEY_REMINDER_SENT: True}
            sent += 1
        if sent:
            await db.flush()
        return sent

    async def notify_scheduled_published(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        post_id: str,
        title: str,
    ) -> NotificationModel:
        """Notify author that scheduled post went live."""
        notification = NotificationModel(
            user_id=user_id,
            notification_type=NOTIFICATION_TYPE_SCHEDULED_PUBLISHED,
            title=EMAIL_SUBJECT_SCHEDULED_PUBLISHED.format(title=title),
            body=NOTIFICATION_BODY_SCHEDULED_PUBLISHED,
            status=NOTIFICATION_STATUS_UNREAD,
            content_id=post_id,
            content_type=CONTENT_TYPE_BLOG_POST,
        )
        db.add(notification)
        await db.flush()
        notification.email_sent = await self._send_email(
            db,
            user_id,
            EMAIL_SUBJECT_SCHEDULED_PUBLISHED.format(title=title),
            NOTIFICATION_BODY_SCHEDULED_PUBLISHED,
        )
        return notification

    async def create_workflow_update(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        notification_type: str,
        title: str,
        body: str,
        content_id: str,
        content_type: str,
    ) -> NotificationModel:
        """Create an in-app workflow status notification."""
        notification = NotificationModel(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            status=NOTIFICATION_STATUS_UNREAD,
            content_id=content_id,
            content_type=content_type,
        )
        db.add(notification)
        await db.flush()
        return notification

    async def _send_email(
        self,
        db: AsyncSession,
        user_id: str,
        subject: str,
        body: str,
    ) -> bool:
        """Log email delivery attempt; returns True when dispatched."""
        user = await db.get(UserModel, user_id)
        if user is None:
            return False
        logger.info(
            "email_notification",
            to=user.email,
            subject=subject,
            body_preview=body[:120],
        )
        return True


__all__ = ["NotificationService"]
