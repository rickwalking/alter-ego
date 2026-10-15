"""autopilot pov topics and the owner-confirmed thesis

Revision ID: b1c2d3e4f5a6
Revises: b0c1d2e3f4a5
Create Date: 2026-10-15

AE-0377 (ADR-0021): ADDITIVE. ``topic_candidates`` gains the scout v3
``content_mode`` (NULL = Radar IA) and the POV ``thesis_draft``;
``autopilot_runs`` gains ``pov_thesis``, the thesis the owner confirmed on
Telegram before generation. Every column is nullable; no existing column is
altered or dropped. The new run state ``awaiting_thesis`` fits the existing
``state`` column (no constraint lists the states). ``downgrade`` drops the
three columns.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = "b0c1d2e3f4a5"
branch_labels = None
depends_on = None

_TOPICS = "topic_candidates"
_RUNS = "autopilot_runs"
_MODE_LENGTH = 20
_THESIS_LENGTH = 280


def upgrade() -> None:
    """Add the POV columns."""
    op.add_column(
        _TOPICS, sa.Column("content_mode", sa.String(_MODE_LENGTH), nullable=True)
    )
    op.add_column(
        _TOPICS, sa.Column("thesis_draft", sa.String(_THESIS_LENGTH), nullable=True)
    )
    op.add_column(
        _RUNS, sa.Column("pov_thesis", sa.String(_THESIS_LENGTH), nullable=True)
    )


def downgrade() -> None:
    """Drop the POV columns."""
    op.drop_column(_RUNS, "pov_thesis")
    op.drop_column(_TOPICS, "thesis_draft")
    op.drop_column(_TOPICS, "content_mode")
