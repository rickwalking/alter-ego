"""autopilot topic candidate image style and guidance

Revision ID: e7f8a9b0c1d2
Revises: d1e2f3a4b5c6
Create Date: 2026-10-14

ADDITIVE. ``topic_candidates`` gains the scout's image preset
(``image_style``, NOT NULL, server default ``neo_anime`` so existing rows get
the default) and its optional visual direction (``image_guidance``). No
existing column is altered or dropped, so the LangGraph checkpoint-drain rule
does not apply. ``downgrade`` drops what ``upgrade`` added.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e7f8a9b0c1d2"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None

_TOPICS = "topic_candidates"
_IMAGE_STYLE = "image_style"
_IMAGE_GUIDANCE = "image_guidance"
_IMAGE_STYLE_LENGTH = 32
_DEFAULT_STYLE = "neo_anime"


def upgrade() -> None:
    """Add the image style and guidance columns."""
    op.add_column(
        _TOPICS,
        sa.Column(
            _IMAGE_STYLE,
            sa.String(_IMAGE_STYLE_LENGTH),
            nullable=False,
            server_default=_DEFAULT_STYLE,
        ),
    )
    op.add_column(_TOPICS, sa.Column(_IMAGE_GUIDANCE, sa.Text(), nullable=True))


def downgrade() -> None:
    """Drop the image style and guidance columns."""
    op.drop_column(_TOPICS, _IMAGE_GUIDANCE)
    op.drop_column(_TOPICS, _IMAGE_STYLE)
