"""carousel generation events

Revision ID: e7a91c4d2f60
Revises: d1b0cf9cd80d
Create Date: 2026-10-26

ADDITIVE. One append-only, content-free diagnostic table and three indexes.
Production receives the same ORM-compiled DDL through the existing idempotent
``generation_queue_schema --apply --verify`` deploy one-shot.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "e7a91c4d2f60"
down_revision = "d1b0cf9cd80d"
branch_labels = None
depends_on = None

_TABLE = "carousel_generation_events"
_JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
_INDEXES = (
    (
        "ix_carousel_generation_events_project_occurred",
        ("carousel_project_id", "occurred_at", "id"),
    ),
    (
        "ix_carousel_generation_events_run_occurred",
        ("generation_run_id", "occurred_at", "id"),
    ),
    ("ix_carousel_generation_events_occurred_at", ("occurred_at",)),
)


def _inspector() -> sa.engine.reflection.Inspector:
    return sa.inspect(op.get_bind())


def _has_table() -> bool:
    return bool(_inspector().has_table(_TABLE))


def _index_names() -> set[str]:
    return {str(index["name"]) for index in _inspector().get_indexes(_TABLE)}


def upgrade() -> None:
    """Create the event table and indexes when missing."""
    if not _has_table():
        op.create_table(
            _TABLE,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("generation_run_id", sa.Uuid(), nullable=False),
            sa.Column("carousel_project_id", sa.String(36), nullable=False),
            sa.Column("kind", sa.String(32), nullable=False),
            sa.Column("event_type", sa.String(64), nullable=False),
            sa.Column("phase", sa.String(64), nullable=True),
            sa.Column("outcome", sa.String(24), nullable=False),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("duration_ms", sa.BigInteger(), nullable=True),
            sa.Column("attempt", sa.SmallInteger(), nullable=True),
            sa.Column("error_code", sa.String(64), nullable=True),
            sa.Column("message_code", sa.String(64), nullable=True),
            sa.Column("details", _JSON, nullable=False),
            sa.Column("langfuse_trace_id", sa.String(128), nullable=True),
            sa.Column("langfuse_trace_url", sa.String(512), nullable=True),
            sa.ForeignKeyConstraint(
                ["generation_run_id"], ["generation_runs.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["carousel_project_id"], ["carousel_projects.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    existing = _index_names()
    for name, columns in _INDEXES:
        if name not in existing:
            op.create_index(name, _TABLE, list(columns))


def downgrade() -> None:
    """Drop event indexes and the table when present."""
    if not _has_table():
        return
    existing = _index_names()
    for name, _columns in _INDEXES:
        if name in existing:
            op.drop_index(name, table_name=_TABLE)
    op.drop_table(_TABLE)
