"""autopilot served signal urls

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-10-13

ADDITIVE. Topic intake allows a source URL only when that URL was
served in the signals bundle within the last 6 hours. The 30-minute bundle
cache is shorter than that window, so the served set is stored. No existing
table is altered, so the LangGraph checkpoint-drain gate does not apply.
``downgrade`` drops the new table.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None

_TABLE = "autopilot_served_urls"
_INDEX = "idx_autopilot_served_urls_served_at"
_URL = "url"
_SERVED_AT = "served_at"


def upgrade() -> None:
    """Create the served-URL allowlist table and its time index."""
    op.create_table(
        _TABLE,
        sa.Column(_URL, sa.Text(), primary_key=True, nullable=False),
        sa.Column(_SERVED_AT, sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(_INDEX, _TABLE, [_SERVED_AT])


def downgrade() -> None:
    """Drop the served-URL allowlist table."""
    op.drop_index(_INDEX, table_name=_TABLE)
    op.drop_table(_TABLE)
