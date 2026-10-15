"""instagram per-post insights snapshots

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-10-15

AE-0378 (ADR-0021 D11): ADDITIVE. One new table, ``instagram_post_insights``:
one row per Instagram media id holding the latest Graph insights snapshot.
Every metric column is nullable (NULL = the Graph API did not return it, shown
as "n/d"). No existing table or column is altered or dropped. ``downgrade``
drops the table.
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


def upgrade() -> None:
    """Create the insights snapshot table."""
    op.create_table(
        _INSIGHTS,
        sa.Column("media_id", sa.String(_IG_ID_LENGTH), nullable=False),
        *(sa.Column(name, sa.Integer(), nullable=True) for name in _METRICS),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("media_id"),
    )


def downgrade() -> None:
    """Drop the insights snapshot table."""
    op.drop_table(_INSIGHTS)
