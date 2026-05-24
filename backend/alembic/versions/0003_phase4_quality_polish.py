"""Alembic migration for Phase 4 quality and polish."""

import sqlalchemy as sa

from alembic import op

revision = "0003_phase4_quality_polish"
down_revision = "0002_phase3_workflow_collaboration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "blog_posts",
        sa.Column("ai_disclosure_label", sa.String(50), nullable=True, server_default="none"),
    )
    op.create_index(
        "idx_blog_posts_author_status_updated",
        "blog_posts",
        ["author_id", "status", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_blog_posts_author_status_updated", table_name="blog_posts")
    op.drop_column("blog_posts", "ai_disclosure_label")
