"""autopilot reels repost

Revision ID: c3d4e5f6a7b9
Revises: b2c3d4e5f6a8
Create Date: 2026-11-19

ADDITIVE. Two new tables: ``autopilot_reposts`` (one row per repost draft the
scout submits) and ``autopilot_reel_facts`` (each Reel's probed duration and
collaborators). Two nullable or defaulted columns on ``autopilot_cover_assets``:
``purpose`` (``carousel_cover`` for every existing row) and ``repost_id``. No
existing column is altered or dropped. ``downgrade`` drops what upgrade added.

Idempotent: the backend creates missing tables at startup, so upgrade skips an
existing table or column and downgrade skips a missing one.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "c3d4e5f6a7b9"
down_revision = "b2c3d4e5f6a8"
branch_labels = None
depends_on = None

_REPOSTS = "autopilot_reposts"
_FACTS = "autopilot_reel_facts"
_COVERS = "autopilot_cover_assets"
_JSON = sa.JSON().with_variant(JSONB(), "postgresql")
_ID = 128


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return bool(_inspector().has_table(name))


def _has_column(table: str, column: str) -> bool:
    return any(c["name"] == column for c in _inspector().get_columns(table))


def _ts(name: str, *, nullable: bool = True) -> sa.Column[sa.DateTime]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def _reposts() -> None:
    op.create_table(
        _REPOSTS,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("media_id", sa.String(_ID), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("permalink", sa.String(512), nullable=True),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("hook_text", sa.Text(), nullable=True),
        sa.Column("hook_duration_s", sa.Float(), nullable=False),
        sa.Column("trim_start_s", sa.Float(), nullable=False),
        sa.Column("trim_end_s", sa.Float(), nullable=True),
        sa.Column("cover_asset_id", sa.Uuid(), nullable=True),
        sa.Column("collaborators", _JSON, nullable=False),
        sa.Column("share_to_feed", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        _ts("publish_earliest"),
        _ts("publish_latest"),
        _ts("created_at", nullable=False),
        _ts("expires_at", nullable=False),
        _ts("updated_at", nullable=False),
        sa.Column("cover_choice", sa.String(16), nullable=True),
        _ts("publish_at"),
        _ts("approved_at"),
        sa.Column("decided_by", sa.String(64), nullable=True),
        _ts("preview_ready_at"),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        _ts("caption_edit_at"),
        sa.Column("container_id", sa.String(_ID), nullable=True),
        _ts("container_created_at"),
        sa.Column("new_media_id", sa.String(_ID), nullable=True),
        sa.Column("new_permalink", sa.String(512), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        _ts("published_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_autopilot_reposts_media_created", _REPOSTS, ["media_id", "created_at"]
    )
    op.create_index("ix_autopilot_reposts_status", _REPOSTS, ["status"])


def _facts() -> None:
    op.create_table(
        _FACTS,
        sa.Column("media_id", sa.String(_ID), nullable=False),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("collaborators", _JSON, nullable=False),
        _ts("probed_at", nullable=False),
        sa.PrimaryKeyConstraint("media_id"),
    )


def _cover_columns() -> None:
    if not _has_column(_COVERS, "purpose"):
        op.add_column(
            _COVERS,
            sa.Column(
                "purpose",
                sa.String(16),
                nullable=False,
                server_default="carousel_cover",
            ),
        )
    if not _has_column(_COVERS, "repost_id"):
        op.add_column(_COVERS, sa.Column("repost_id", sa.Uuid(), nullable=True))


def upgrade() -> None:
    """Create the repost tables and the cover columns when missing."""
    if not _has_table(_REPOSTS):
        _reposts()
    if not _has_table(_FACTS):
        _facts()
    if _has_table(_COVERS):
        _cover_columns()


def downgrade() -> None:
    """Drop the cover columns and the repost tables when present."""
    if _has_table(_COVERS):
        for name in ("repost_id", "purpose"):
            if _has_column(_COVERS, name):
                op.drop_column(_COVERS, name)
    for table in (_FACTS, _REPOSTS):
        if _has_table(table):
            op.drop_table(table)
