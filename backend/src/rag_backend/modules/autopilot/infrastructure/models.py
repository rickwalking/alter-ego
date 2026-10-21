"""SQLAlchemy models for the autopilot tables.

Private to the module. ``Mapped[]`` columns mirror the Alembic revision
``autopilot_tables``. ``carousel_project_id`` is ``String(36)`` because
``carousel_projects.id`` is VARCHAR(36); a native UUID cannot foreign-key
to it. Run and topic primary keys are UUIDs.

Document columns are JSON on SQLite (tests) and JSONB on PostgreSQL (ADR-0006).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
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
from rag_backend.domain.constants.content_mode import POV_FORMAT_MAX_CHARS
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
from rag_backend.modules.autopilot.pov_constants import (
    CONTENT_MODE_COLUMN_LENGTH,
    THESIS_DRAFT_MAX_CHARS,
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

_JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class AutopilotOrmBase(DeclarativeBase):
    """Typed declarative base sharing the application's ``Base.metadata``.

    ``declarative_base()`` is typed as Any, so module models cannot subclass it
    under mypy strict. Sharing its metadata keeps ``create_all`` and Alembic
    autogenerate on the same registry.
    """

    metadata = SharedBase.metadata


class TopicCandidateModel(AutopilotOrmBase):
    """ORM row for one scout topic candidate.

    ``content_mode`` NULL means Radar IA; ``pov_format``, ``slide_count``,
    ``quotes`` and ``cover_asset_id`` (an ``autopilot_cover_assets.id``) are NULL
    when absent or default.
    """

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
    image_style: Mapped[str] = mapped_column(
        String(IMAGE_STYLE_MAX_CHARS),
        nullable=False,
        server_default=IMAGE_STYLE_NEO_ANIME,
    )
    image_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_mode: Mapped[str | None] = mapped_column(
        String(CONTENT_MODE_COLUMN_LENGTH), nullable=True
    )
    thesis_draft: Mapped[str | None] = mapped_column(
        String(THESIS_DRAFT_MAX_CHARS), nullable=True
    )
    pov_format: Mapped[str | None] = mapped_column(
        String(POV_FORMAT_MAX_CHARS), nullable=True
    )
    slide_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quotes: Mapped[list[dict[str, str]] | None] = mapped_column(
        _JSON_DOCUMENT, nullable=True
    )
    cover_asset_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    __table_args__ = (UniqueConstraint("signal_hash", name=UQ_TOPIC_SIGNAL_HASH),)


class AutopilotRunModel(AutopilotOrmBase):
    """ORM row for one autopilot run.

    ``publish_attempts`` maps to the ``attempts`` column, which predates the split
    from ``start_attempts``. ``publish_claimed_at`` is the compare-and-set claim
    held while one caller is talking to Graph. The escalated wake scan rotates by
    ``wake_checked_at``, never by ``updated_at``. ``pov_thesis`` is the thesis the
    owner confirmed on Telegram, ``scheduled_at`` the owner's publish time while the
    run is ``scheduled``, and ``cover_chosen`` whether the owner chose the GrokBot
    cover for slide 1 (NULL means no).
    """

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
    publish_claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
    pov_thesis: Mapped[str | None] = mapped_column(
        String(THESIS_DRAFT_MAX_CHARS), nullable=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cover_chosen: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
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

    ``ig_container_id`` is stored before ``media_publish`` so a retry resumes it.
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
    """The Story announcing one carousel. The primary key is the claim:
    one Story per carousel, whichever path published it.

    ``story_container_id`` is stored before ``media_publish`` so a retry resumes it.
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
