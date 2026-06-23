"""add carousel_projects.custom_visual_details

Project-level visual direction injected into every slide image prompt
(AE-0263 backdrop / custom scene details; AE-0261 revision feedback append).

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-23
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the nullable custom_visual_details column."""
    op.add_column(
        "carousel_projects",
        sa.Column("custom_visual_details", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop the custom_visual_details column."""
    op.drop_column("carousel_projects", "custom_visual_details")
