"""Add carousel presentation contract columns and foundation tables."""

import sqlalchemy as sa

from alembic import op
from rag_backend.domain.constants.carousel_presentation import (
    LEGACY_PRESENTATION_POLICY_VERSION,
    MIGRATION_DOWNGRADE_BLOCKED_MESSAGE,
    PRESENTATION_POLICY_HERO_LOWER_THIRD_V1,
)

revision = "0008_carousel_presentation_contract"
down_revision = "0007_add_carousel_image_generations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "carousel_creator_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("media_type", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("relative_path", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_carousel_creator_assets_owner",
        "carousel_creator_assets",
        ["owner_id"],
    )
    op.create_unique_constraint(
        "uq_carousel_creator_assets_content_sha256",
        "carousel_creator_assets",
        ["content_sha256"],
    )

    op.create_table(
        "carousel_artifact_builds",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("carousel_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_version", sa.String(length=80), nullable=False),
        sa.Column("operation_id", sa.String(length=64), nullable=False),
        sa.Column("source_lock_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("staging_path", sa.String(length=500), nullable=True),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_carousel_artifact_builds_project_version",
        "carousel_artifact_builds",
        ["project_id", "artifact_version"],
    )
    op.create_index(
        "idx_carousel_artifact_builds_project",
        "carousel_artifact_builds",
        ["project_id"],
    )
    op.create_index(
        "idx_carousel_artifact_builds_status",
        "carousel_artifact_builds",
        ["status"],
    )

    op.add_column(
        "carousel_projects",
        sa.Column("presentation_policy_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "carousel_projects",
        sa.Column("presentation_policy_checksum", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "carousel_projects",
        sa.Column("artifact_version", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "carousel_projects",
        sa.Column("creator_website", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "carousel_projects",
        sa.Column(
            "creator_asset_id",
            sa.String(length=36),
            sa.ForeignKey("carousel_creator_assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.execute(
        sa.text(
            "UPDATE carousel_projects "
            "SET presentation_policy_version = :legacy_version "
            "WHERE presentation_policy_version IS NULL"
        ).bindparams(legacy_version=LEGACY_PRESENTATION_POLICY_VERSION)
    )


def downgrade() -> None:
    bind = op.get_bind()
    blocked_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM carousel_projects "
            "WHERE presentation_policy_version = :policy_version"
        ),
        {"policy_version": PRESENTATION_POLICY_HERO_LOWER_THIRD_V1},
    ).scalar_one()
    if blocked_count:
        raise RuntimeError(MIGRATION_DOWNGRADE_BLOCKED_MESSAGE)

    op.drop_column("carousel_projects", "creator_asset_id")
    op.drop_column("carousel_projects", "creator_website")
    op.drop_column("carousel_projects", "artifact_version")
    op.drop_column("carousel_projects", "presentation_policy_checksum")
    op.drop_column("carousel_projects", "presentation_policy_version")

    op.drop_index(
        "idx_carousel_artifact_builds_status",
        table_name="carousel_artifact_builds",
    )
    op.drop_index(
        "idx_carousel_artifact_builds_project",
        table_name="carousel_artifact_builds",
    )
    op.drop_constraint(
        "uq_carousel_artifact_builds_project_version",
        "carousel_artifact_builds",
        type_="unique",
    )
    op.drop_table("carousel_artifact_builds")

    op.drop_constraint(
        "uq_carousel_creator_assets_content_sha256",
        "carousel_creator_assets",
        type_="unique",
    )
    op.drop_index(
        "idx_carousel_creator_assets_owner",
        table_name="carousel_creator_assets",
    )
    op.drop_table("carousel_creator_assets")
