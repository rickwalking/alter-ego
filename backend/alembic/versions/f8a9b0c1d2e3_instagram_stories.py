"""instagram stories announcing a published carousel

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-10-14

ADDITIVE. One new table, ``instagram_stories``: one row per carousel
holds the Story that announces it (state, the container id and creation time
stored before ``media_publish``, the Story media id, the last error). The
primary key is the idempotency key, for both the autopilot run and the manual
route. No existing table or column is altered or dropped, so the LangGraph
checkpoint-drain rule does not apply. ``downgrade`` drops the table.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "f8a9b0c1d2e3"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None

_STORIES = "instagram_stories"
_FK_PROJECT = "fk_instagram_stories_carousel_project"
_PROJECT_FK_TARGET = "carousel_projects.id"
_ID_LENGTH = 36
_STATE_LENGTH = 32
_IG_ID_LENGTH = 128


def upgrade() -> None:
    """Create the Story table."""
    op.create_table(
        _STORIES,
        sa.Column("carousel_project_id", sa.String(_ID_LENGTH), nullable=False),
        sa.Column("state", sa.String(_STATE_LENGTH), nullable=False),
        sa.Column("story_container_id", sa.String(_IG_ID_LENGTH), nullable=True),
        sa.Column(
            "story_container_created_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("story_media_id", sa.String(_IG_ID_LENGTH), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["carousel_project_id"],
            [_PROJECT_FK_TARGET],
            name=_FK_PROJECT,
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("carousel_project_id"),
    )


def downgrade() -> None:
    """Drop the Story table."""
    op.drop_table(_STORIES)
