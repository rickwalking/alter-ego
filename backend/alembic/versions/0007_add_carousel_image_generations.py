"""Add carousel image generation attempt records."""

import sqlalchemy as sa

from alembic import op

revision = "0007_add_carousel_image_generations"
down_revision = "0006_add_slide_layout_strategy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "carousel_image_generations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("carousel_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "slide_id",
            sa.String(length=36),
            sa.ForeignKey("carousel_slides.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slide_number", sa.Integer(), nullable=False),
        sa.Column("generation_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("output_path", sa.String(length=500), nullable=True),
        sa.Column("prompt_hash", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=30), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("style", sa.String(length=64), nullable=True),
        sa.Column("raw_prompt", sa.Text(), nullable=True),
        sa.Column("rendered_prompt", sa.Text(), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
        sa.Column("provider_image_id", sa.String(length=128), nullable=True),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_unique_constraint(
        "uq_carousel_image_generations_key",
        "carousel_image_generations",
        ["generation_key"],
    )
    op.create_index(
        "idx_carousel_image_generations_project",
        "carousel_image_generations",
        ["project_id"],
    )
    op.create_index(
        "idx_carousel_image_generations_slide",
        "carousel_image_generations",
        ["slide_id"],
    )
    op.create_index(
        "idx_carousel_image_generations_status",
        "carousel_image_generations",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_carousel_image_generations_status",
        table_name="carousel_image_generations",
    )
    op.drop_index(
        "idx_carousel_image_generations_slide",
        table_name="carousel_image_generations",
    )
    op.drop_index(
        "idx_carousel_image_generations_project",
        table_name="carousel_image_generations",
    )
    op.drop_constraint(
        "uq_carousel_image_generations_key",
        "carousel_image_generations",
        type_="unique",
    )
    op.drop_table("carousel_image_generations")
