"""SQLAlchemy model of ``image_bridge_jobs``.

Mirrors the Alembic revision ``image_bridge_jobs``. ``image_bytes`` holds
the callback image only between the callback and the waiter's single read;
the waiter nulls it.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, LargeBinary, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from rag_backend.infrastructure.database.config import Base as SharedBase
from rag_backend.modules.image_bridge.constants import (
    ERROR_CODE_LENGTH,
    INDEX_JOBS_STATUS_EXPIRES_AT,
    SIZE_LENGTH,
    STATUS_LENGTH,
    TABLE_IMAGE_BRIDGE_JOBS,
    TOKEN_SHA256_LENGTH,
)


class ImageBridgeOrmBase(DeclarativeBase):
    """Typed declarative base sharing the application's ``Base.metadata``."""

    metadata = SharedBase.metadata


class ImageBridgeJobModel(ImageBridgeOrmBase):
    """ORM row for one bridge job.

    ``image_bytes`` is deferred: the 2 s poll reads the status, never the bytes.
    """

    __tablename__ = TABLE_IMAGE_BRIDGE_JOBS
    __table_args__ = (Index(INDEX_JOBS_STATUS_EXPIRES_AT, "status", "expires_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True)
    status: Mapped[str] = mapped_column(String(STATUS_LENGTH), nullable=False)
    size: Mapped[str] = mapped_column(String(SIZE_LENGTH), nullable=False)
    token_sha256: Mapped[str] = mapped_column(
        String(TOKEN_SHA256_LENGTH), nullable=False
    )
    image_bytes: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True, deferred=True
    )
    error_code: Mapped[str | None] = mapped_column(
        String(ERROR_CODE_LENGTH), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
