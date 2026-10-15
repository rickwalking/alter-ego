"""SQLAlchemy models for the autopilot tables.

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

from rag_backend.domain.constants import IMAGE_STYLE_NEO_ANIME
from rag_backend.infrastructure.database.config import Base as SharedBase
from rag_backend.modules.autopilot.carousel_constants import IMAGE_STYLE_MAX_CHARS
from rag_backend.modules.autopilot.constants import (
    CAROUSEL_PROJECT_FK,
    CAROUSEL_PROJECT_ID_LENGTH,
    FK_RUNS_CAROUSEL_PROJECT,
    FK_RUNS_TOPIC_CANDIDATE,
    IG_IDENTIFIER_LENGTH,
    INDEX_RUNS_STATE_UPDATED_AT,
    INDEX_SERVED_URLS_SERVED_AT,
    ON_DELETE_RESTRICT,
    ON_DELETE_SET_NULL,
    PROVIDER_LENGTH,
    SIGNAL_HASH_LENGTH,
    STATE_LENGTH,
    STATUS_LENGTH,
    TABLE_AUTOPILOT_RUNS,
    TABLE_INTEGRATION_CREDENTIALS,
    TABLE_SERVED_SIGNAL_URLS,
    TABLE_TELEGRAM_UPDATES,
    TABLE_TOPIC_CANDIDATES,
    TABLE_X_SIGNALS,
    TOPIC_CANDIDATE_FK,
    UQ_RUNS_CAROUSEL_PROJECT,
    UQ_TOPIC_SIGNAL_HASH,
)
from rag_backend.modules.autopilot.recovery_constants import (
    FK_MANUAL_PUBLISH_PROJECT,
    NOTIFY_CURSOR_NAME_LENGTH,
    ON_DELETE_CASCADE,
    OUTBOX_EVENT_ID_LENGTH,
    REWORK_PHASE_LENGTH,
    TABLE_MANUAL_PUBLISHES,
    TABLE_NOTIFY_CURSOR,
)
from rag_backend.modules.autopilot.schedule_constants import (
    INDEX_RUNS_STATE_SCHEDULED_AT,
)
from rag_backend.modules.autopilot.story_constants import (
    FK_STORY_PROJECT,
    TABLE_INSTAGRAM_STORIES,
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
    # AE-0361: the scout's image preset and optional visual direction.
    image_style: Mapped[str] = mapped_column(
        String(IMAGE_STYLE_MAX_CHARS),
        nullable=False,
        server_default=IMAGE_STYLE_NEO_ANIME,
    )
    image_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    # The ``attempts`` column predates the split; it counts publish attempts.
    publish_attempts: Mapped[int] = mapped_column(
        "attempts", Integer, nullable=False, default=0, server_default="0"
    )
    start_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    rework_phase: Mapped[str | None] = mapped_column(
        String(REWORK_PHASE_LENGTH), nullable=True
    )
    rework_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalated_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Compare-and-set claim held while one caller is talking to Graph.
    publish_claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # QA r2 R1: the escalated wake scan rotates by this, never by updated_at.
    wake_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    telegram_message_ids: Mapped[list[int] | dict[str, object]] = mapped_column(
        _JSON_DOCUMENT, nullable=False
    )
    ig_container_id: Mapped[str | None] = mapped_column(
        String(IG_IDENTIFIER_LENGTH), nullable=True
    )
    ig_container_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ig_post_id: Mapped[str | None] = mapped_column(
        String(IG_IDENTIFIER_LENGTH), nullable=True
    )
    ig_permalink: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AE-0370: the owner's publish time while the run is ``scheduled``.
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("carousel_project_id", name=UQ_RUNS_CAROUSEL_PROJECT),
        Index(INDEX_RUNS_STATE_UPDATED_AT, "state", "updated_at"),
        Index(INDEX_RUNS_STATE_SCHEDULED_AT, "state", "scheduled_at"),
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


class ServedSignalUrlModel(AutopilotOrmBase):
    """A signal URL returned by GET /signals, kept for the 6 hour allowlist."""

    __tablename__ = TABLE_SERVED_SIGNAL_URLS

    url: Mapped[str] = mapped_column(Text, primary_key=True)
    served_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index(INDEX_SERVED_URLS_SERVED_AT, "served_at"),)


class TelegramUpdateModel(AutopilotOrmBase):
    """ORM row for one seen Telegram update id."""

    __tablename__ = TABLE_TELEGRAM_UPDATES

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class XBrowserSignalModel(AutopilotOrmBase):
    """One X status the Grok Bot observed in its own browser."""

    __tablename__ = TABLE_X_SIGNALS

    url: Mapped[str] = mapped_column(Text, primary_key=True)
    handle: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    likes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reposts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    replies: Mapped[int | None] = mapped_column(Integer, nullable=True)
    views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(STATUS_LENGTH), nullable=False)
    stored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ManualPublishModel(AutopilotOrmBase):
    """Owner-triggered Instagram publish for a carousel without an autopilot run.

    The primary key is the claim: one row per carousel, so two concurrent
    manual publishes cannot both call Graph.
    """

    __tablename__ = TABLE_MANUAL_PUBLISHES

    carousel_project_id: Mapped[str] = mapped_column(
        String(CAROUSEL_PROJECT_ID_LENGTH),
        ForeignKey(
            CAROUSEL_PROJECT_FK,
            name=FK_MANUAL_PUBLISH_PROJECT,
            ondelete=ON_DELETE_CASCADE,
        ),
        primary_key=True,
    )
    state: Mapped[str] = mapped_column(String(STATE_LENGTH), nullable=False)
    ig_post_id: Mapped[str | None] = mapped_column(
        String(IG_IDENTIFIER_LENGTH), nullable=True
    )
    ig_permalink: Mapped[str | None] = mapped_column(Text, nullable=True)
    # QA r2 R4b: stored before ``media_publish`` so a retry resumes it.
    ig_container_id: Mapped[str | None] = mapped_column(
        String(IG_IDENTIFIER_LENGTH), nullable=True
    )
    ig_container_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class InstagramStoryModel(AutopilotOrmBase):
    """The Story announcing one carousel (AE-0369). The primary key is the claim:
    one Story per carousel, whichever path published it.
    """

    __tablename__ = TABLE_INSTAGRAM_STORIES

    carousel_project_id: Mapped[str] = mapped_column(
        String(CAROUSEL_PROJECT_ID_LENGTH),
        ForeignKey(
            CAROUSEL_PROJECT_FK,
            name=FK_STORY_PROJECT,
            ondelete=ON_DELETE_CASCADE,
        ),
        primary_key=True,
    )
    state: Mapped[str] = mapped_column(String(STATE_LENGTH), nullable=False)
    # Stored before ``media_publish`` so a retry resumes it.
    story_container_id: Mapped[str | None] = mapped_column(
        String(IG_IDENTIFIER_LENGTH), nullable=True
    )
    story_container_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    story_media_id: Mapped[str | None] = mapped_column(
        String(IG_IDENTIFIER_LENGTH), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NotifyCursorModel(AutopilotOrmBase):
    """The Telegram notifier's position in the outbox (created_at, event_id)."""

    __tablename__ = TABLE_NOTIFY_CURSOR

    name: Mapped[str] = mapped_column(
        String(NOTIFY_CURSOR_NAME_LENGTH), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    event_id: Mapped[str] = mapped_column(
        String(OUTBOX_EVENT_ID_LENGTH), nullable=False
    )
