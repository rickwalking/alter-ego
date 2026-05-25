"""SQLAlchemy model for in-app notifications (NOTIF-001)."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSON

from rag_backend.infrastructure.database.config import Base


class NotificationModel(Base):
    """User notification for review requests, reminders, and workflow updates."""

    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="unread")
    content_id = Column(String(36), nullable=True)
    content_type = Column(String(50), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    email_sent = Column(Boolean, nullable=False, default=False)
    deadline_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_notifications_user_status", "user_id", "status"),
        Index("idx_notifications_deadline", "deadline_at"),
        Index("idx_notifications_content", "content_type", "content_id"),
    )


__all__ = ["NotificationModel"]
