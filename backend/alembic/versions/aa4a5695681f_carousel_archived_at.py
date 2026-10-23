"""carousel archived_at

Revision ID: aa4a5695681f
Revises: c7d8e9f0a1b3
Create Date: 2026-10-23

``carousel_projects.archived_at`` (nullable, timezone-aware) marks a carousel the
owner archived, or that the workflow worker archived after it sat idle (Pedro's
decision): archived carousels leave the workflow board and raise no alerts. A
restore sets it back to NULL. Indexed, since the board and the alert queries
filter on it. Not a LangGraph checkpoint table: the checkpoint-drain rule does
not apply. ``downgrade`` drops the index and the column.

prod: the deploy does not run alembic, so the same column reaches prod through the
idempotent one-shot ``python -m rag_backend.scripts.carousel_archived_at --apply
--verify`` that deploy.yml runs after the palette timestamptz step.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "aa4a5695681f"
down_revision = "c7d8e9f0a1b3"
branch_labels = None
depends_on = None

_TABLE = "carousel_projects"
_COLUMN = "archived_at"
_INDEX = "idx_carousel_projects_archived_at"


def upgrade() -> None:
    """Add the nullable ``archived_at`` column and its index."""
    op.add_column(
        _TABLE,
        sa.Column(_COLUMN, sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(_INDEX, _TABLE, [_COLUMN])


def downgrade() -> None:
    """Drop the index and the column."""
    op.drop_index(_INDEX, table_name=_TABLE)
    op.drop_column(_TABLE, _COLUMN)
