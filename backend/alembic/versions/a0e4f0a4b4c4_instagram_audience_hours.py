"""instagram audience hours cache

Revision ID: a0e4f0a4b4c4
Revises: d3e4f5a6b7c8
Create Date: 2026-10-16

ADDITIVE. One new table, ``instagram_audience_hours``: one row per
Instagram account caching the Graph ``online_followers`` insight (followers
online per UTC hour) for the Telegram schedule picker's recommendations.
``checked_at`` is the last Graph attempt (read at most once a day);
``fetched_at`` is the last success. No existing table or column is altered or
dropped. ``downgrade`` drops the table.

Idempotent like the earlier autopilot revisions: prod has no ``alembic_version`` and the
backend creates missing tables at startup, so upgrade skips an existing table
and downgrade skips a missing one.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "a0e4f0a4b4c4"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None

_AUDIENCE = "instagram_audience_hours"
_IG_ID_LENGTH = 128


def _has_table() -> bool:
    return bool(sa.inspect(op.get_bind()).has_table(_AUDIENCE))


def upgrade() -> None:
    """Create the audience cache table (if missing)."""
    if _has_table():
        return
    op.create_table(
        _AUDIENCE,
        sa.Column("ig_user_id", sa.String(_IG_ID_LENGTH), nullable=False),
        sa.Column(
            "online_followers",
            sa.JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("ig_user_id"),
    )


def downgrade() -> None:
    """Drop the audience cache table (if present)."""
    if not _has_table():
        return
    op.drop_table(_AUDIENCE)
