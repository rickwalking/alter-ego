"""instagram per-post insights snapshots

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-10-15

ADR-0021: ADDITIVE. One new table, ``instagram_post_insights``:
one row per Instagram media id holding the latest Graph insights snapshot.
Every metric column is nullable (NULL = the Graph API did not return it, shown
as "n/d"). No existing table or column is altered or dropped. ``downgrade``
drops the table.

Idempotent: prod has no ``alembic_version`` table and the SQL
was applied by hand, so the table is created only when missing and dropped only
when present.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None

_INSIGHTS = "instagram_post_insights"
_IG_ID_LENGTH = 128
_METRICS = (
    "views",
    "reach",
    "saved",
    "shares",
    "follows",
    "profile_visits",
    "total_interactions",
)


def _has_table() -> bool:
    return bool(sa.inspect(op.get_bind()).has_table(_INSIGHTS))


def upgrade() -> None:
    """Create the insights snapshot table (if missing)."""
    if _has_table():
        return
    op.create_table(
        _INSIGHTS,
        sa.Column("media_id", sa.String(_IG_ID_LENGTH), nullable=False),
        *(sa.Column(name, sa.Integer(), nullable=True) for name in _METRICS),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("media_id"),
    )


def downgrade() -> None:
    """Drop the insights snapshot table (if present)."""
    if not _has_table():
        return
    op.drop_table(_INSIGHTS)
