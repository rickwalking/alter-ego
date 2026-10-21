"""autopilot x browser signals

Revision ID: c8d9e0f1a2b3
Revises: f2a3b4c5d6e7
Create Date: 2026-10-14

ADDITIVE. Grok Bot posts observed X status URLs. Valid items are
stored as ``x_browser`` signals and their canonical URLs join the topic
allowlist. No existing table is altered, so the LangGraph checkpoint-drain
gate does not apply. ``downgrade`` drops the new table.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "c8d9e0f1a2b3"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None

_TABLE = "autopilot_x_signals"
_SOURCE_LENGTH = 64
_URL = "url"
_HANDLE = "handle"
_TEXT = "text"
_LIKES = "likes"
_REPOSTS = "reposts"
_REPLIES = "replies"
_VIEWS = "views"
_OBSERVED_AT = "observed_at"
_POSTED_AT = "posted_at"
_SOURCE = "source"
_STORED_AT = "stored_at"


def upgrade() -> None:
    """Create the browser-observed X signal table."""
    op.create_table(
        _TABLE,
        sa.Column(_URL, sa.Text(), primary_key=True, nullable=False),
        sa.Column(_HANDLE, sa.Text(), nullable=False),
        sa.Column(_TEXT, sa.Text(), nullable=False),
        sa.Column(_LIKES, sa.Integer(), nullable=True),
        sa.Column(_REPOSTS, sa.Integer(), nullable=True),
        sa.Column(_REPLIES, sa.Integer(), nullable=True),
        sa.Column(_VIEWS, sa.Integer(), nullable=True),
        sa.Column(_OBSERVED_AT, sa.DateTime(timezone=True), nullable=False),
        sa.Column(_POSTED_AT, sa.DateTime(timezone=True), nullable=False),
        sa.Column(_SOURCE, sa.String(length=_SOURCE_LENGTH), nullable=False),
        sa.Column(_STORED_AT, sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Drop the browser-observed X signal table."""
    op.drop_table(_TABLE)
