"""SQLAlchemy model of ``generation_runs``.

Mirrors the Alembic revision that creates the table; the deploy one-shot compiles
its DDL from this table, so the migration, the ORM and prod cannot drift. The
partial unique index on ``dedupe_key`` covers the active statuses only: a finished
or dead-lettered run frees its key for the next unit of work.
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
    SmallInteger,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from rag_backend.infrastructure.database.config import Base as SharedBase
from rag_backend.modules.generation_queue.constants import (
    ACTIVE_STATUSES,
    DEDUPE_KEY_LENGTH,
    ERROR_CODE_LENGTH,
    EVENT_TYPE_LENGTH,
    INDEX_ACTIVE_DEDUPE,
    INDEX_AUTOPILOT_RUN,
    INDEX_EVENT_OCCURRED,
    INDEX_EVENT_PROJECT_OCCURRED,
    INDEX_EVENT_RUN_OCCURRED,
    INDEX_PROJECT,
    INDEX_STATUS_CREATED,
    KIND_LENGTH,
    MESSAGE_CODE_LENGTH,
    OUTCOME_LENGTH,
    PHASE_LENGTH,
    STATUS_LENGTH,
    TABLE_CAROUSEL_GENERATION_EVENTS,
    TABLE_GENERATION_RUNS,
    TRACE_ID_LENGTH,
    TRACE_URL_LENGTH,
)

ACTIVE_WHERE_SQL = "status IN ({})".format(
    ", ".join(f"'{status}'" for status in ACTIVE_STATUSES)
)
_JSON = JSON().with_variant(JSONB(), "postgresql")
_ID_LENGTH = 36


class GenerationQueueOrmBase(DeclarativeBase):
    """Typed declarative base sharing the application's ``Base.metadata``."""

    metadata = SharedBase.metadata


class GenerationRunModel(GenerationQueueOrmBase):
    """ORM row for one generation run."""

    __tablename__ = TABLE_GENERATION_RUNS
    __table_args__ = (
        Index(INDEX_STATUS_CREATED, "status", "created_at"),
        Index(
            INDEX_ACTIVE_DEDUPE,
            "dedupe_key",
            unique=True,
            postgresql_where=text(ACTIVE_WHERE_SQL),
            sqlite_where=text(ACTIVE_WHERE_SQL),
        ),
        Index(INDEX_PROJECT, "carousel_project_id"),
        Index(INDEX_AUTOPILOT_RUN, "autopilot_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True)
    kind: Mapped[str] = mapped_column(String(KIND_LENGTH), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(DEDUPE_KEY_LENGTH), nullable=False)
    status: Mapped[str] = mapped_column(String(STATUS_LENGTH), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(_JSON, nullable=False)
    autopilot_run_id: Mapped[str | None] = mapped_column(
        String(_ID_LENGTH), nullable=True
    )
    carousel_project_id: Mapped[str | None] = mapped_column(
        String(_ID_LENGTH), nullable=True
    )
    pgq_job_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    phase_attempts: Mapped[dict[str, int]] = mapped_column(_JSON, nullable=False)
    last_phase: Mapped[str | None] = mapped_column(String(PHASE_LENGTH), nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error_code: Mapped[str | None] = mapped_column(
        String(ERROR_CODE_LENGTH), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class CarouselGenerationEventModel(GenerationQueueOrmBase):
    """Append-only, content-free diagnostic event for one carousel run."""

    __tablename__ = TABLE_CAROUSEL_GENERATION_EVENTS
    __table_args__ = (
        Index(
            INDEX_EVENT_PROJECT_OCCURRED,
            "carousel_project_id",
            "occurred_at",
            "id",
        ),
        Index(INDEX_EVENT_RUN_OCCURRED, "generation_run_id", "occurred_at", "id"),
        Index(INDEX_EVENT_OCCURRED, "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True)
    generation_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("generation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    carousel_project_id: Mapped[str] = mapped_column(
        String(_ID_LENGTH),
        ForeignKey("carousel_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(KIND_LENGTH), nullable=False)
    event_type: Mapped[str] = mapped_column(String(EVENT_TYPE_LENGTH), nullable=False)
    phase: Mapped[str | None] = mapped_column(String(PHASE_LENGTH), nullable=True)
    outcome: Mapped[str] = mapped_column(String(OUTCOME_LENGTH), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    attempt: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    error_code: Mapped[str | None] = mapped_column(
        String(ERROR_CODE_LENGTH), nullable=True
    )
    message_code: Mapped[str | None] = mapped_column(
        String(MESSAGE_CODE_LENGTH), nullable=True
    )
    details: Mapped[dict[str, object]] = mapped_column(_JSON, nullable=False)
    langfuse_trace_id: Mapped[str | None] = mapped_column(
        String(TRACE_ID_LENGTH), nullable=True
    )
    langfuse_trace_url: Mapped[str | None] = mapped_column(
        String(TRACE_URL_LENGTH), nullable=True
    )
