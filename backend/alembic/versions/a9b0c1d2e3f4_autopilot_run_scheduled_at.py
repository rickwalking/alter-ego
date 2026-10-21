"""autopilot run scheduled publish time

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-10-15

ADDITIVE. One nullable column, ``autopilot_runs.scheduled_at``
(TIMESTAMPTZ), holds the owner's publish time while a run is ``scheduled``,
plus the index ``(state, scheduled_at)`` the due scan reads. Existing rows keep
NULL, which means "not scheduled". No existing column is altered or dropped,
so the LangGraph checkpoint-drain rule does not apply. ``downgrade`` drops the
index and the column.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "a9b0c1d2e3f4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None

_RUNS = "autopilot_runs"
_SCHEDULED_AT = "scheduled_at"
_STATE = "state"
_INDEX = "idx_autopilot_runs_state_scheduled_at"


def upgrade() -> None:
    """Add the scheduled publish time and its due-scan index."""
    op.add_column(
        _RUNS,
        sa.Column(_SCHEDULED_AT, sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(_INDEX, _RUNS, [_STATE, _SCHEDULED_AT])


def downgrade() -> None:
    """Drop the index, then the column."""
    op.drop_index(_INDEX, table_name=_RUNS)
    op.drop_column(_RUNS, _SCHEDULED_AT)
