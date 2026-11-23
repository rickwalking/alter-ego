"""autopilot repost sources

Revision ID: d4e5f6a7b8c0
Revises: c3d4e5f6a7b9
Create Date: 2026-11-23

ADDITIVE. One new table, ``autopilot_repost_sources``: each source video the
scout uploads for a repost draft, and the draft that used it. No existing
table or column is touched. ``downgrade`` drops the table.

Idempotent: the backend creates missing tables at startup, so upgrade skips an
existing table and downgrade skips a missing one.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d4e5f6a7b8c0"
down_revision = "c3d4e5f6a7b9"
branch_labels = None
depends_on = None

_SOURCES = "autopilot_repost_sources"


def _has_table(name: str) -> bool:
    return bool(sa.inspect(op.get_bind()).has_table(name))


def upgrade() -> None:
    """Create the sources table and its two indexes."""
    if _has_table(_SOURCES):
        return
    op.create_table(
        _SOURCES,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("codec", sa.String(32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("duration_s", sa.Float(), nullable=False),
        sa.Column("repost_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_autopilot_repost_sources_created_at", _SOURCES, ["created_at"]
    )
    op.create_index("ix_autopilot_repost_sources_repost_id", _SOURCES, ["repost_id"])


def downgrade() -> None:
    """Drop the sources table."""
    if _has_table(_SOURCES):
        op.drop_table(_SOURCES)
