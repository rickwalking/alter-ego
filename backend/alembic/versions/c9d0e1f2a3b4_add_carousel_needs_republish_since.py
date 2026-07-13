"""add carousel needs_republish_since marker (AE-0314)

Adds one nullable timestamp column to ``carousel_projects``:

- ``needs_republish_since`` — stamped in the SAME transaction as a
  post-completion slide-text edit (AE-0314). NULL means "no rebuild owed".
  A non-NULL value older than a few minutes is swept by the workflow
  watchdog, which republishes the carousel from its persisted slides and
  clears the marker — the server-guaranteed republish (cold-critic r6: a
  browser closed between the edit 200 and the republish call must still
  converge to a fresh PDF).

Purely additive (nullable timestamp), safe on the drifted prod DB. Recovery
is roll-forward.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None

_TABLE = "carousel_projects"
_COLUMN = "needs_republish_since"


def upgrade() -> None:
    """Add needs_republish_since (nullable timestamptz)."""
    op.add_column(
        _TABLE,
        sa.Column(_COLUMN, sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Drop the needs_republish_since marker column."""
    op.drop_column(_TABLE, _COLUMN)
