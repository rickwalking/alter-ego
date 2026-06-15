"""Add slide_layout_strategy column to carousel_projects.

The column stores the user's preferred slide layout strategy name
(nullable TEXT, no FK constraint). The ORM model already declares it
at CarouselProjectModel.slide_layout_strategy.
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_add_slide_layout_strategy"
down_revision = "0005_add_persona_corrections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "carousel_projects",
        sa.Column("slide_layout_strategy", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("carousel_projects", "slide_layout_strategy")
