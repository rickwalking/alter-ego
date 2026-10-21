"""palette timestamps timezone-aware

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-10-21

AE-0446: ``palettes.created_at`` / ``updated_at`` were the only
``timestamp without time zone`` columns. Domain models move to aware UTC
times (``domain.clock.utc_now``, PR #170), which asyncpg rejects for a naive
column, so palette writes would fail on Postgres. The existing naive values were written
as UTC, so they are converted with ``AT TIME ZONE 'UTC'`` (no value shifts).
Not a LangGraph checkpoint table: the checkpoint-drain rule does not apply.
``downgrade`` converts back to naive UTC.

prod: the deploy does not run alembic (AE-0207), so the same ALTER reaches
prod through the idempotent one-shot ``python -m
rag_backend.scripts.palette_timestamptz --apply --verify`` that deploy.yml
runs after the blog cutover (owner decision D-6; no manual ALTER).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None

_TABLE = "palettes"
_COLUMNS = ("created_at", "updated_at")
_UTC = "UTC"
_POSTGRES = "postgresql"


def _is_postgres() -> bool:
    # SQLite has no timezone-aware timestamp type (nor ALTER COLUMN TYPE):
    # both column shapes are stored identically there, so nothing to alter.
    return op.get_bind().dialect.name == _POSTGRES


def upgrade() -> None:
    """Make the palette timestamps ``timestamptz`` (values read as UTC)."""
    if not _is_postgres():
        return
    for column in _COLUMNS:
        op.alter_column(
            _TABLE,
            column,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=False,
            postgresql_using=f"{column} AT TIME ZONE '{_UTC}'",
        )


def downgrade() -> None:
    """Back to naive ``timestamp`` holding the UTC wall time."""
    if not _is_postgres():
        return
    for column in _COLUMNS:
        op.alter_column(
            _TABLE,
            column,
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            postgresql_using=f"{column} AT TIME ZONE '{_UTC}'",
        )
