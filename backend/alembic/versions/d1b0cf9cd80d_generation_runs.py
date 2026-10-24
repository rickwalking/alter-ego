"""generation runs

Revision ID: d1b0cf9cd80d
Revises: aa4a5695681f
Create Date: 2026-10-23

ADR-0026: ADDITIVE. One new table, ``generation_runs``: the carousel generation
queue's own record of each unit of work (an autopilot drive or a dashboard resume),
the source of truth for Telegram, the dashboard and idempotency. The partial unique
index on ``dedupe_key`` covers the active statuses only. No existing table or
column is altered. ``downgrade`` drops the table and its indexes.

prod: the deploy does not run alembic; the same DDL, compiled from the ORM table,
reaches prod through the idempotent one-shot ``python -m
rag_backend.scripts.generation_queue_schema --apply --verify``, which also installs
PgQueuer's own tables. Each step here is skipped when already present.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "d1b0cf9cd80d"
down_revision = "aa4a5695681f"
branch_labels = None
depends_on = None

_TABLE = "generation_runs"
_ACTIVE = "status IN ('queued', 'running', 'retry_wait')"
_JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
_INDEXES: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    ("ix_generation_runs_status_created_at", ("status", "created_at"), False),
    ("uq_generation_runs_active_dedupe_key", ("dedupe_key",), True),
    ("ix_generation_runs_carousel_project_id", ("carousel_project_id",), False),
    ("ix_generation_runs_autopilot_run_id", ("autopilot_run_id",), False),
)


def _inspector() -> sa.engine.reflection.Inspector:
    return sa.inspect(op.get_bind())


def _has_table() -> bool:
    return bool(_inspector().has_table(_TABLE))


def _index_names() -> set[str]:
    return {str(index["name"]) for index in _inspector().get_indexes(_TABLE)}


def upgrade() -> None:
    """Create the table and its four indexes (each if missing)."""
    if not _has_table():
        op.create_table(
            _TABLE,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("kind", sa.String(32), nullable=False),
            sa.Column("dedupe_key", sa.String(160), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("payload", _JSON, nullable=False),
            sa.Column("autopilot_run_id", sa.String(36), nullable=True),
            sa.Column("carousel_project_id", sa.String(36), nullable=True),
            sa.Column("pgq_job_id", sa.BigInteger(), nullable=True),
            sa.Column("attempts", sa.SmallInteger(), nullable=False),
            sa.Column("phase_attempts", _JSON, nullable=False),
            sa.Column("last_phase", sa.String(64), nullable=True),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error_code", sa.String(64), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    existing = _index_names()
    for name, columns, unique in _INDEXES:
        if name in existing:
            continue
        where = sa.text(_ACTIVE) if unique else None
        op.create_index(
            name,
            _TABLE,
            list(columns),
            unique=unique,
            postgresql_where=where,
            sqlite_where=where,
        )


def downgrade() -> None:
    """Drop the indexes and the table (each if present)."""
    if not _has_table():
        return
    existing = _index_names()
    for name, _columns, _unique in _INDEXES:
        if name in existing:
            op.drop_index(name, table_name=_TABLE)
    op.drop_table(_TABLE)
