"""add documents scope and is_public

Revision ID: a1b2c3d4e5f6
Revises: 63eaefa67b8c
Create Date: 2026-06-14 21:00:00.000000

AE-0090: additive, data-preserving columns on `documents`. The `Document`
entity already carries `scope` (DocumentScope) and `is_public` (bool), but the
squashed baseline never persisted them. Both columns are NOT NULL with
server_defaults, so existing rows are backfilled (`scope='personal'`,
`is_public=false`) without a separate UPDATE.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "63eaefa67b8c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add scope and is_public to documents with backfilling server defaults."""
    op.add_column(
        "documents",
        sa.Column(
            "scope",
            sa.String(length=20),
            server_default="personal",
            nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "is_public",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Drop the additive scope and is_public columns from documents."""
    op.drop_column("documents", "is_public")
    op.drop_column("documents", "scope")
