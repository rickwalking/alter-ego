"""ORM rows for repost drafts and the Reel facts cache (ADR-0031)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from rag_backend.modules.autopilot.constants import IG_IDENTIFIER_LENGTH
from rag_backend.modules.autopilot.infrastructure.models import AutopilotOrmBase
from rag_backend.modules.autopilot.repost_constants import (
    ACTOR_LENGTH,
    CODE_LENGTH,
    COVER_CHOICE_LENGTH,
    ERROR_MESSAGE_LENGTH,
    HASH_LENGTH,
    INDEX_REPOSTS_MEDIA,
    INDEX_REPOSTS_STATUS,
    KEY_LENGTH,
    PERMALINK_LENGTH,
    STATUS_LENGTH,
    TABLE_REEL_FACTS,
    TABLE_REPOSTS,
)

_JSON = JSON().with_variant(JSONB(), "postgresql")
_TS = DateTime(timezone=True)


class RepostModel(AutopilotOrmBase):
    """One repost draft. The API key can only insert ``pending_approval`` rows."""

    __tablename__ = TABLE_REPOSTS
    __table_args__ = (
        Index(INDEX_REPOSTS_MEDIA, "media_id", "created_at"),
        Index(INDEX_REPOSTS_STATUS, "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(KEY_LENGTH), unique=True)
    request_hash: Mapped[str] = mapped_column(String(HASH_LENGTH))
    media_id: Mapped[str] = mapped_column(String(IG_IDENTIFIER_LENGTH))
    status: Mapped[str] = mapped_column(String(STATUS_LENGTH))
    permalink: Mapped[str | None] = mapped_column(String(PERMALINK_LENGTH))
    caption: Mapped[str] = mapped_column(Text)
    hook_text: Mapped[str | None] = mapped_column(Text)
    hook_duration_s: Mapped[float] = mapped_column(Float)
    trim_start_s: Mapped[float] = mapped_column(Float)
    trim_end_s: Mapped[float | None] = mapped_column(Float)
    cover_asset_id: Mapped[UUID | None] = mapped_column(nullable=True)
    collaborators: Mapped[list[str]] = mapped_column(_JSON)
    share_to_feed: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    publish_earliest: Mapped[datetime | None] = mapped_column(_TS)
    publish_latest: Mapped[datetime | None] = mapped_column(_TS)
    created_at: Mapped[datetime] = mapped_column(_TS)
    expires_at: Mapped[datetime] = mapped_column(_TS)
    updated_at: Mapped[datetime] = mapped_column(_TS)
    cover_choice: Mapped[str | None] = mapped_column(String(COVER_CHOICE_LENGTH))
    publish_at: Mapped[datetime | None] = mapped_column(_TS)
    approved_at: Mapped[datetime | None] = mapped_column(_TS)
    decided_by: Mapped[str | None] = mapped_column(String(ACTOR_LENGTH))
    preview_ready_at: Mapped[datetime | None] = mapped_column(_TS)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    caption_edit_at: Mapped[datetime | None] = mapped_column(_TS)
    container_id: Mapped[str | None] = mapped_column(String(IG_IDENTIFIER_LENGTH))
    container_created_at: Mapped[datetime | None] = mapped_column(_TS)
    new_media_id: Mapped[str | None] = mapped_column(String(IG_IDENTIFIER_LENGTH))
    new_permalink: Mapped[str | None] = mapped_column(String(PERMALINK_LENGTH))
    error_code: Mapped[str | None] = mapped_column(String(CODE_LENGTH))
    error_message: Mapped[str | None] = mapped_column(String(ERROR_MESSAGE_LENGTH))
    published_at: Mapped[datetime | None] = mapped_column(_TS)


class ReelFactsModel(AutopilotOrmBase):
    """Duration and collaborators of one Reel, probed once."""

    __tablename__ = TABLE_REEL_FACTS

    media_id: Mapped[str] = mapped_column(
        String(IG_IDENTIFIER_LENGTH), primary_key=True
    )
    duration_s: Mapped[float | None] = mapped_column(Float)
    collaborators: Mapped[list[str]] = mapped_column(_JSON)
    probed_at: Mapped[datetime] = mapped_column(_TS)


__all__ = ["ReelFactsModel", "RepostModel"]
