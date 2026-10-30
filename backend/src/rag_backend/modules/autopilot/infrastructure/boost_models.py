"""ORM rows for boost requests and their audit events."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from rag_backend.modules.autopilot.boost_constants import (
    INDEX_STATUS_NEXT,
    OPEN_WHERE_SQL,
    TABLE_BOOST_EVENTS,
    TABLE_BOOST_REQUESTS,
    UQ_MEDIA_ACTIVE,
)
from rag_backend.modules.autopilot.constants import IG_IDENTIFIER_LENGTH
from rag_backend.modules.autopilot.infrastructure.models import AutopilotOrmBase

_JSON = JSON().with_variant(JSONB(), "postgresql")


class BoostRequestModel(AutopilotOrmBase):
    """One owner-approved boost. The bot can only insert pending rows."""

    __tablename__ = TABLE_BOOST_REQUESTS
    __table_args__ = (
        Index(INDEX_STATUS_NEXT, "status", "next_attempt_at"),
        Index(
            UQ_MEDIA_ACTIVE,
            "media_id",
            unique=True,
            postgresql_where=text(OPEN_WHERE_SQL),
            sqlite_where=text(OPEN_WHERE_SQL),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    media_id: Mapped[str] = mapped_column(String(IG_IDENTIFIER_LENGTH))
    status: Mapped[str] = mapped_column(String(24))
    objective: Mapped[str] = mapped_column(String(24))
    daily_budget_cents: Mapped[int] = mapped_column(Integer)
    days: Mapped[int] = mapped_column(Integer)
    total_budget_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    audience: Mapped[dict[str, object]] = mapped_column(_JSON)
    reason: Mapped[str] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    permalink: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    meta_campaign_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta_adset_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta_creative_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta_ad_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    launch_attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_insights: Mapped[dict[str, int | None] | None] = mapped_column(
        _JSON, nullable=True
    )
    insights_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BoostEventModel(AutopilotOrmBase):
    """One status change. Detail never contains a token."""

    __tablename__ = TABLE_BOOST_EVENTS

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{TABLE_BOOST_REQUESTS}.id"),
    )
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    from_status: Mapped[str] = mapped_column(String(24))
    to_status: Mapped[str] = mapped_column(String(24))
    actor: Mapped[str] = mapped_column(String(64))
    detail: Mapped[dict[str, str]] = mapped_column(_JSON)


__all__ = ["BoostEventModel", "BoostRequestModel"]
