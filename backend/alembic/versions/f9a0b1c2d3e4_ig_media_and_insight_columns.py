"""ig media list and extra insight columns

Revision ID: f9a0b1c2d3e4
Revises: e7a91c4d2f60
Create Date: 2026-10-29

ADR-0029: additive. New table ``ig_media`` and four nullable columns on
``instagram_post_insights``. No existing column is altered. Idempotent so a
database that already has the objects is left alone.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "f9a0b1c2d3e4"
down_revision = "e7a91c4d2f60"
branch_labels = None
depends_on = None

_MEDIA = "ig_media"
_INSIGHTS = "instagram_post_insights"
_INDEX = "ix_ig_media_posted_at"
_IG_ID = 128
_EXCERPT = 280
_TYPE = 32
_PRODUCT = 16
_NEW_COLUMNS = (
    "likes",
    "comments",
    "avg_watch_time_ms",
    "total_watch_time_ms",
)


def _has_table(name: str) -> bool:
    return bool(sa.inspect(op.get_bind()).has_table(name))


def _has_column(table: str, name: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(table)
    return any(column["name"] == name for column in columns)


def upgrade() -> None:
    """Create ``ig_media`` and add the nullable insight columns."""
    if not _has_table(_MEDIA):
        op.create_table(
            _MEDIA,
            sa.Column("media_id", sa.String(_IG_ID), nullable=False),
            sa.Column("media_type", sa.String(_TYPE), nullable=False),
            sa.Column("media_product_type", sa.String(_PRODUCT), nullable=True),
            sa.Column("permalink", sa.Text(), nullable=True),
            sa.Column("caption_excerpt", sa.String(_EXCERPT), nullable=True),
            sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("like_count", sa.Integer(), nullable=True),
            sa.Column("comments_count", sa.Integer(), nullable=True),
            sa.Column("listed_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("media_id"),
        )
        op.create_index(_INDEX, _MEDIA, ["posted_at"])
    if not _has_table(_INSIGHTS):
        return
    for name in _NEW_COLUMNS:
        if not _has_column(_INSIGHTS, name):
            op.add_column(_INSIGHTS, sa.Column(name, sa.Integer(), nullable=True))


def downgrade() -> None:
    """Drop the new columns and ``ig_media``."""
    if _has_table(_INSIGHTS):
        for name in _NEW_COLUMNS:
            if _has_column(_INSIGHTS, name):
                op.drop_column(_INSIGHTS, name)
    if not _has_table(_MEDIA):
        return
    op.drop_index(_INDEX, table_name=_MEDIA)
    op.drop_table(_MEDIA)
