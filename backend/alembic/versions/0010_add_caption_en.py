"""Add English Instagram caption column to carousel projects."""

import sqlalchemy as sa

from alembic import op

revision = "0010_add_caption_en"
down_revision = "0009_creator_asset_owner_sha256_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "carousel_projects",
        sa.Column("caption_en", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("carousel_projects", "caption_en")
