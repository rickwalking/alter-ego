"""Add workflow_status column to carousel_projects."""

import sqlalchemy as sa

from alembic import op

revision = "0003_add_carousel_workflow_status"
down_revision = "0003_phase4_quality_polish"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "carousel_projects",
        sa.Column(
            "workflow_status",
            sa.String(length=50),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("carousel_projects", "workflow_status")
