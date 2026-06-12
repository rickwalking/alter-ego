"""Scope creator asset uniqueness to owner plus content hash."""

import sqlalchemy as sa

from alembic import op

revision = "0009_creator_asset_owner_sha256_unique"
down_revision = "0008_carousel_presentation_contract"
branch_labels = None
depends_on = None

_OWNER_SHA_CONSTRAINT = "uq_carousel_creator_assets_owner_sha256"
_GLOBAL_SHA_CONSTRAINT = "uq_carousel_creator_assets_content_sha256"


def upgrade() -> None:
    op.drop_constraint(_GLOBAL_SHA_CONSTRAINT, "carousel_creator_assets", type_="unique")
    op.create_unique_constraint(
        _OWNER_SHA_CONSTRAINT,
        "carousel_creator_assets",
        ["owner_id", "content_sha256"],
    )


def downgrade() -> None:
    op.drop_constraint(_OWNER_SHA_CONSTRAINT, "carousel_creator_assets", type_="unique")
    op.create_unique_constraint(
        _GLOBAL_SHA_CONSTRAINT,
        "carousel_creator_assets",
        ["content_sha256"],
    )
