"""carousel cover generations

Revision ID: 344dec4495d3
Revises: aa4a5695681f
Create Date: 2026-10-23

ADDITIVE. One new table, ``carousel_cover_generations``: one row per slide-1
cover the Grok Bot generates from the owner's library photos (status, prompt
SHA-256, photo count, model, cost, result asset, error code, created/started/
completed times; ``started_at`` is set when the job gets its bridge slot). It is
the budget log behind the caps (4 per carousel, 40 per month): deleting the
carousel or the result image sets its reference to NULL and keeps the row. No existing
table or column is altered or dropped. ``downgrade`` drops the table and its
indexes.

Idempotent like the image bridge revision: prod has no ``alembic_version`` and
the backend creates missing tables (with their indexes) at startup, so upgrade
skips an existing table or index and downgrade skips missing ones. No deploy
one-shot is needed for a new table.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "344dec4495d3"
down_revision = "aa4a5695681f"
branch_labels = None
depends_on = None

_TABLE = "carousel_cover_generations"
_INDEX_PROJECT = "idx_carousel_cover_generations_project"
_INDEX_OWNER_CREATED = "idx_carousel_cover_generations_owner_created"
_ID_LENGTH = 36
_STATUS_LENGTH = 16
_SHA256_LENGTH = 64
_MODEL_LENGTH = 64
_ERROR_CODE_LENGTH = 64
_ERROR_DETAIL_LENGTH = 300


def _inspector() -> sa.engine.reflection.Inspector:
    return sa.inspect(op.get_bind())


def _has_table() -> bool:
    return bool(_inspector().has_table(_TABLE))


def _indexes() -> set[str]:
    return {str(index["name"]) for index in _inspector().get_indexes(_TABLE)}


def upgrade() -> None:
    """Create the generation table and its two indexes (each if missing)."""
    if not _has_table():
        op.create_table(
            _TABLE,
            sa.Column("id", sa.String(_ID_LENGTH), nullable=False),
            sa.Column(
                "project_id",
                sa.String(_ID_LENGTH),
                sa.ForeignKey("carousel_projects.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "owner_id",
                sa.String(_ID_LENGTH),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("status", sa.String(_STATUS_LENGTH), nullable=False),
            sa.Column("prompt_sha256", sa.String(_SHA256_LENGTH), nullable=False),
            sa.Column("photo_count", sa.Integer(), nullable=False),
            sa.Column("model", sa.String(_MODEL_LENGTH), nullable=False),
            sa.Column("cost_usd", sa.Float(), nullable=False),
            sa.Column(
                "result_asset_id",
                sa.String(_ID_LENGTH),
                sa.ForeignKey("carousel_creator_assets.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("error_code", sa.String(_ERROR_CODE_LENGTH), nullable=True),
            sa.Column("error_detail", sa.String(_ERROR_DETAIL_LENGTH), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    existing = _indexes()
    if _INDEX_PROJECT not in existing:
        op.create_index(_INDEX_PROJECT, _TABLE, ["project_id"])
    if _INDEX_OWNER_CREATED not in existing:
        op.create_index(_INDEX_OWNER_CREATED, _TABLE, ["owner_id", "created_at"])


def downgrade() -> None:
    """Drop the generation table and its indexes (each if present)."""
    if not _has_table():
        return
    existing = _indexes()
    for index in (_INDEX_OWNER_CREATED, _INDEX_PROJECT):
        if index in existing:
            op.drop_index(index, table_name=_TABLE)
    op.drop_table(_TABLE)
