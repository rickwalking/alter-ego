"""SQLAlchemy models for the four autopilot tables.

Private to the module. ``Mapped[]`` columns mirror the Alembic revision
``autopilot_tables``. ``carousel_project_id`` is ``String(36)`` because
``carousel_projects.id`` is VARCHAR(36); a native UUID cannot foreign-key
to it. Run and topic primary keys are UUIDs.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from rag_backend.infrastructure.database.config import Base as SharedBase
from rag_backend.modules.autopilot.constants import (
    CAROUSEL_PROJECT_FK,
    CAROUSEL_PROJECT_ID_LENGTH,
    FK_RUNS_CAROUSEL_PROJECT,
    FK_RUNS_TOPIC_CANDIDATE,
    IG_IDENTIFIER_LENGTH,
    INDEX_RUNS_STATE_UPDATED_AT,
    ON_DELETE_RESTRICT,
    ON_DELETE_SET_NULL,
    PROVIDER_LENGTH,
    SIGNAL_HASH_LENGTH,
    STATE_LENGTH,
    STATUS_LENGTH,
    TABLE_AUTOPILOT_RUNS,
    TABLE_INTEGRATION_CREDENTIALS,
    TABLE_TELEGRAM_UPDATES,
    TABLE_TOPIC_CANDIDATES,
    TOPIC_CANDIDATE_FK,
    UQ_RUNS_CAROUSEL_PROJECT,
    UQ_TOPIC_SIGNAL_HASH,
)

# JSON on SQLite (tests), JSONB on PostgreSQL (prod, ADR-0006).
_JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class AutopilotOrmBase(DeclarativeBase):
    """Typed declarative base sharing the application's ``Base.metadata``.

    ``declarative_base()`` is typed as Any, so module models cannot subclass it
    under mypy strict. Sharing its metadata keeps ``create_all`` and Alembic
    autogenerate on the same registry.
    """

    metadata = SharedBase.metadata


class TopicCandidateModel(AutopilotOrmBase):
    """ORM row for one scout topic candidate."""

    __tablename__ = TABLE_TOPIC_CANDIDATES

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    angle: Mapped[str] = mapped_column(Text, nullable=False)
    why_viral: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(Text, nullable=False)
    niche: Mapped[str] = mapped_column(Text, nullable=False)
    brief: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[str]] = mapped_column(_JSON_DOCUMENT, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_hash: Mapped[str] = mapped_column(String(SIGNAL_HASH_LENGTH), nullable=False)
    status: Mapped[str] = mapped_column(String(STATUS_LENGTH), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("signal_hash", name=UQ_TOPIC_SIGNAL_HASH),)


class AutopilotRunModel(AutopilotOrmBase):
    """ORM row for one autopilot run."""

    __tablename__ = TABLE_AUTOPILOT_RUNS

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    carousel_project_id: Mapped[str | None] = mapped_column(
        String(CAROUSEL_PROJECT_ID_LENGTH),
        ForeignKey(
            CAROUSEL_PROJECT_FK,
            name=FK_RUNS_CAROUSEL_PROJECT,
            ondelete=ON_DELETE_SET_NULL,
        ),
        nullable=True,
    )
    topic_candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            TOPIC_CANDIDATE_FK,
            name=FK_RUNS_TOPIC_CANDIDATE,
            ondelete=ON_DELETE_RESTRICT,
        ),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(String(STATE_LENGTH), nullable=False)
    state_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    telegram_message_ids: Mapped[list[int]] = mapped_column(
        _JSON_DOCUMENT, nullable=False
    )
    ig_container_id: Mapped[str | None] = mapped_column(
        String(IG_IDENTIFIER_LENGTH), nullable=True
    )
    ig_post_id: Mapped[str | None] = mapped_column(
        String(IG_IDENTIFIER_LENGTH), nullable=True
    )
    ig_permalink: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("carousel_project_id", name=UQ_RUNS_CAROUSEL_PROJECT),
        Index(INDEX_RUNS_STATE_UPDATED_AT, "state", "updated_at"),
    )


class IntegrationCredentialModel(AutopilotOrmBase):
    """ORM row for one encrypted provider token."""

    __tablename__ = TABLE_INTEGRATION_CREDENTIALS

    provider: Mapped[str] = mapped_column(String(PROVIDER_LENGTH), primary_key=True)
    encrypted_token: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TelegramUpdateModel(AutopilotOrmBase):
    """ORM row for one seen Telegram update id."""

    __tablename__ = TABLE_TELEGRAM_UPDATES

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
