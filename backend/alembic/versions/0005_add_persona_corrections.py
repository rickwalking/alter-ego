"""Add persona_corrections table for feedback learning."""

import sqlalchemy as sa

from alembic import op

revision = "0005_add_persona_corrections"
down_revision = "0004_add_carousel_assigned_reviewer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "persona_corrections",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "persona_id",
            sa.String(length=36),
            sa.ForeignKey("persona_profiles.id"),
            nullable=False,
        ),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("corrected_text", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "correction_type",
            sa.String(length=64),
            nullable=False,
            server_default="content",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_persona_corrections_persona_id",
        "persona_corrections",
        ["persona_id"],
    )
    op.create_index(
        "idx_persona_corrections_created_at",
        "persona_corrections",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_persona_corrections_created_at", table_name="persona_corrections"
    )
    op.drop_index(
        "idx_persona_corrections_persona_id", table_name="persona_corrections"
    )
    op.drop_table("persona_corrections")
