"""Add assigned_reviewer_id to carousel_projects."""

import sqlalchemy as sa

from alembic import op

revision = "0004_add_carousel_assigned_reviewer"
down_revision = "0003_add_carousel_workflow_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "carousel_projects",
        sa.Column(
            "assigned_reviewer_id",
            sa.String(length=36),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("carousel_projects", "assigned_reviewer_id")
