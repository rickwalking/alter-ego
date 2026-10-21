"""autopilot container created at

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-10-13

ADDITIVE. Instagram containers expire after 24 hours. ``updated_at``
moves on every retry, so the reuse window needs its own timestamp.
``downgrade`` drops the column.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None

_RUNS = "autopilot_runs"
_COLUMN = "ig_container_created_at"


def upgrade() -> None:
    """Add the container-creation timestamp used by the 24h reuse rule."""
    op.add_column(
        _RUNS,
        sa.Column(_COLUMN, sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Drop the container-creation timestamp."""
    op.drop_column(_RUNS, _COLUMN)
