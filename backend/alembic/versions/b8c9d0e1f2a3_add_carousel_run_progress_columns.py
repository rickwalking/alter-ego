"""add carousel run-progress + fencing columns (AE-0315)

Adds the three run-visibility columns to ``carousel_projects``:

- ``run_started_at``  — stamped when a revision run flips ``phase_status`` to
  ``in_progress``; cleared atomically with any value-changing transition out.
- ``run_heartbeat_at`` — heartbeaten by the background resume task (~60s and
  at stage boundaries). NULL for rows predating this migration: the stale-run
  reaper treats NULL as alert-only forever (migration-day safety — a run
  alive across this deploy must never be reaped on the first tick).
- ``run_epoch`` — monotonic fencing token (default 0). Only the reaper
  increments it; run-owned writers compare their captured epoch against it.

Purely additive (nullable timestamps + defaulted int), safe on the drifted
prod DB. Recovery is roll-forward.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None

_TABLE = "carousel_projects"


def upgrade() -> None:
    """Add run_started_at / run_heartbeat_at / run_epoch."""
    op.add_column(
        _TABLE,
        sa.Column("run_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        _TABLE,
        sa.Column("run_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "run_epoch",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    """Drop the run-progress columns."""
    op.drop_column(_TABLE, "run_epoch")
    op.drop_column(_TABLE, "run_heartbeat_at")
    op.drop_column(_TABLE, "run_started_at")
