"""add palettes catalog table + carousel theme widening + theme_snapshot

Creates the global custom-palette catalog (AE-0269), widens
``carousel_projects.theme`` from varchar(30) to varchar(64) so it can hold a
36-char custom-palette UUID reference, and adds the ``theme_snapshot`` JSONB
column that freezes a carousel's resolved palette at generation (ADR-0019 D9).

All changes are additive / widening (no data rewrite, no narrowing), so the
upgrade is safe on the drifted prod DB. Recovery is roll-forward.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-23
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create palettes, widen theme, add theme_snapshot."""
    op.create_table(
        "palettes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("primary", sa.String(length=7), nullable=False),
        sa.Column("accent", sa.String(length=7), nullable=False),
        sa.Column("background", sa.String(length=7), nullable=False),
        sa.Column("mode", sa.String(length=8), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column(
            "archived", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # Active names unique (archived excluded so a name frees up on archive);
    # slugs globally unique (incl. archived).
    op.create_index(
        "uq_palettes_name_active",
        "palettes",
        ["name"],
        unique=True,
        postgresql_where=sa.text("archived = false"),
    )
    op.create_index("uq_palettes_slug", "palettes", ["slug"], unique=True)

    # Widen theme to hold a 36-char custom-palette UUID reference (AE-0268 left
    # it varchar(30); root keys + "auto" still fit). Widening only — no rewrite.
    op.alter_column(
        "carousel_projects",
        "theme",
        existing_type=sa.String(length=30),
        type_=sa.String(length=64),
        existing_nullable=False,
    )

    # Snapshot of the resolved palette frozen at generation (D9).
    op.add_column(
        "carousel_projects",
        sa.Column("theme_snapshot", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Reverse the additive changes (roll-forward preferred in prod)."""
    op.drop_column("carousel_projects", "theme_snapshot")
    op.alter_column(
        "carousel_projects",
        "theme",
        existing_type=sa.String(length=64),
        type_=sa.String(length=30),
        existing_nullable=False,
    )
    op.drop_index("uq_palettes_slug", table_name="palettes")
    op.drop_index("uq_palettes_name_active", table_name="palettes")
    op.drop_table("palettes")
