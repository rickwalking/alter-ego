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
    INDEX_ACTIVE_DEDUPE,
    INDEX_AUTOPILOT_RUN,
    INDEX_PROJECT,
    INDEX_STATUS_CREATED,
    KIND_LENGTH,
    PHASE_LENGTH,
    STATUS_LENGTH,
    TABLE_GENERATION_RUNS,
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
