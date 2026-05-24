"""SQLAlchemy model for collaborative editing locks (WF-005, UI-021)."""

import uuid

from sqlalchemy import Column, DateTime, Index, String, func

from rag_backend.infrastructure.database.config import Base


class ContentLockModel(Base):
    """Short-lived edit lock to prevent concurrent write conflicts."""

    __tablename__ = "content_locks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id = Column(String(36), nullable=False)
    content_type = Column(String(50), nullable=False)
    user_id = Column(String(36), nullable=False)
    user_name = Column(String(255), nullable=False, default="")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_content_locks_content", "content_type", "content_id", unique=True),
        Index("idx_content_locks_expires", "expires_at"),
    )


__all__ = ["ContentLockModel"]
