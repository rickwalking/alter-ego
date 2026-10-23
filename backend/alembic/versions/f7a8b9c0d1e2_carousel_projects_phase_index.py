"""carousel_projects (phase_status, current_phase) index

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-10-22

The reaper, the parked-workflow guard and the dashboard filter carousels by
``phase_status`` and ``current_phase``; without an index each of those reads
scans ``carousel_projects``. Not a LangGraph checkpoint table: the
checkpoint-drain rule does not apply.

prod: the deploy does not run alembic, so the same index reaches prod through
the idempotent one-shot ``python -m rag_backend.scripts.carousel_phase_index
--apply --verify`` (``CREATE INDEX IF NOT EXISTS``, stack down) that deploy.yml
runs after the palette timestamptz step.
"""

from __future__ import annotations

from alembic import op

revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None

_TABLE = "carousel_projects"
_INDEX = "idx_carousel_projects_phase_status_current_phase"
_COLUMNS = ["phase_status", "current_phase"]
_POSTGRES = "postgresql"


def _is_postgres() -> bool:
    """The SQLite migration fixtures stamp a reduced ``carousel_projects`` without the
    phase columns, and SQLite databases are only used by tests, so the index is
    Postgres-only like the palette change below it.
    """
    return op.get_bind().dialect.name == _POSTGRES


def upgrade() -> None:
    """Create the composite phase index (a no-op when it already exists)."""
    if not _is_postgres():
        return
    op.create_index(_INDEX, _TABLE, _COLUMNS, if_not_exists=True)


def downgrade() -> None:
    """Drop the composite phase index."""
    if not _is_postgres():
        return
    op.drop_index(_INDEX, table_name=_TABLE, if_exists=True)
