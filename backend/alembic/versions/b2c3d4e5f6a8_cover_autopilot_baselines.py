"""cover autopilot baselines

Revision ID: b2c3d4e5f6a8
Revises: c0d1e2f3a4b5
Create Date: 2026-11-04

ADDITIVE. One new table, ``carousel_cover_autopilot_baselines``: one row per
cover generation the autopilot started for a fresh carousel, with slide 1's
cover fields when it was scheduled (``slide_cover_asset_id``,
``hook_asset_id``; plain ids, no foreign key). The drive's gates read it, so a
restart between the cover succeeding and the next gate never loses the cover
or the owner's choice. Deleting the generation deletes its row. No existing
table or column is altered or dropped. ``downgrade`` drops the table.

Idempotent like the cover generations revision: the backend creates missing
tables at startup, so upgrade skips an existing table and downgrade skips a
missing one. No deploy one-shot is needed for a new table.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b2c3d4e5f6a8"
down_revision = "c0d1e2f3a4b5"
branch_labels = None
depends_on = None

_TABLE = "carousel_cover_autopilot_baselines"
_ID_LENGTH = 36


def _has_table() -> bool:
    return bool(sa.inspect(op.get_bind()).has_table(_TABLE))


def upgrade() -> None:
    """Create the baseline table when missing."""
    if _has_table():
        return
    op.create_table(
        _TABLE,
        sa.Column(
            "generation_id",
            sa.String(_ID_LENGTH),
            sa.ForeignKey("carousel_cover_generations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slide_cover_asset_id", sa.String(_ID_LENGTH), nullable=True),
        sa.Column("hook_asset_id", sa.String(_ID_LENGTH), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("generation_id"),
    )


def downgrade() -> None:
    """Drop the baseline table when present."""
    if _has_table():
        op.drop_table(_TABLE)
