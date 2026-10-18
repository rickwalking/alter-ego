"""grok slide-1 cover asset

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-10-17

AE-0418 (ADR-0024): ADDITIVE. New table ``autopilot_cover_assets`` (one row per
GrokBot cover upload; the image is a ``carousel_creator_assets`` row with role
``cover``). Three nullable columns: ``topic_candidates.cover_asset_id`` (the
cover a topic names), ``autopilot_runs.cover_chosen`` (the owner's slide-1
choice) and ``carousel_projects.slide_cover`` (the cover a project renders).
No existing column is altered or dropped. ``downgrade`` removes all four.

Idempotent like the AE-0371 / AE-0406 revisions: prod has no
``alembic_version`` table and applies the SQL by hand, so the table and each
column are created only when missing and dropped only when present.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None

_COVERS = "autopilot_cover_assets"
_INDEX = "ix_autopilot_cover_assets_created_at"


def _columns() -> tuple[tuple[str, str, sa.types.TypeEngine[object]], ...]:
    return (
        ("topic_candidates", "cover_asset_id", sa.Uuid()),
        ("autopilot_runs", "cover_chosen", sa.Boolean()),
        ("carousel_projects", "slide_cover", sa.JSON()),
    )


def _has_column(table: str, name: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(table)
    return any(column["name"] == name for column in columns)


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    """Create the cover table and add the three columns (if missing)."""
    if not _has_table(_COVERS):
        op.create_table(
            _COVERS,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "creator_asset_id",
                sa.String(36),
                sa.ForeignKey(
                    "carousel_creator_assets.id",
                    name="fk_autopilot_cover_assets_creator_asset",
                    ondelete="CASCADE",
                ),
                nullable=False,
            ),
            sa.Column("kind", sa.String(16), nullable=False),
            sa.Column("source_url", sa.String(2048), nullable=True),
            sa.Column("width", sa.Integer(), nullable=False),
            sa.Column("height", sa.Integer(), nullable=False),
            sa.Column(
                "topic_candidate_id",
                sa.Uuid(),
                sa.ForeignKey(
                    "topic_candidates.id",
                    name="fk_autopilot_cover_assets_topic",
                    ondelete="SET NULL",
                ),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(_INDEX, _COVERS, ["created_at"])
    for table, name, column_type in _columns():
        if _has_column(table, name):
            continue
        op.add_column(table, sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    """Drop the three columns and the cover table (only those present)."""
    for table, name, _column_type in reversed(_columns()):
        if not _has_column(table, name):
            continue
        op.drop_column(table, name)
    if _has_table(_COVERS):
        op.drop_index(_INDEX, table_name=_COVERS)
        op.drop_table(_COVERS)
