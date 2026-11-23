"""ORM row of an owner-supplied repost source video."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from rag_backend.modules.autopilot.infrastructure.models import AutopilotOrmBase
from rag_backend.modules.autopilot.repost_constants import KEY_LENGTH
from rag_backend.modules.autopilot.repost_source_constants import (
    CODEC_LENGTH,
    INDEX_REPOST_SOURCES_CREATED,
    INDEX_REPOST_SOURCES_REPOST,
    TABLE_REPOST_SOURCES,
)

_TS = DateTime(timezone=True)


class RepostSourceModel(AutopilotOrmBase):
    """One uploaded source video; ``repost_id`` is set once a draft uses it."""

    __tablename__ = TABLE_REPOST_SOURCES
    __table_args__ = (
        Index(INDEX_REPOST_SOURCES_CREATED, "created_at"),
        Index(INDEX_REPOST_SOURCES_REPOST, "repost_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(KEY_LENGTH))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    codec: Mapped[str] = mapped_column(String(CODEC_LENGTH))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    duration_s: Mapped[float] = mapped_column(Float)
    repost_id: Mapped[UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(_TS)


__all__ = ["RepostSourceModel"]
