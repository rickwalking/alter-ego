"""add event_outbox transactional outbox table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-15 12:00:00.000000

AE-0130: ADDITIVE, behavior-preserving, reversible.

Adds the ``event_outbox`` table backing the transactional-outbox publish path.
``WorkflowEventService.emit`` writes one row here in the **same transaction** as
the state change; a relay is the sole Redis publisher (selects unpublished rows,
publishes the stored payload, marks them published). The migration is **purely
additive** — it only creates a new table and drops nothing — so the LangGraph
checkpoint-drain gate does NOT block it.

The table mirrors ``EventOutboxModel`` so the autogenerate drift check stays
empty, and applies identically on SQLite (tests) and Postgres (prod).
``downgrade`` drops the table, restoring the pre-migration schema.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

# --- Constants -----------------------------------------------------------------
_TABLE = "event_outbox"


def upgrade() -> None:
    """Create the additive event_outbox table + its indexes."""
    op.create_table(
        _TABLE,
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("aggregate_id", sa.String(length=36), nullable=False),
        sa.Column("aggregate_type", sa.String(length=50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", JSON(), nullable=False),
        sa.Column("metadata", JSON(), nullable=False),
        sa.Column("event_timestamp", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "attempts", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("idx_outbox_unpublished", _TABLE, ["published_at"])
    op.create_index("idx_outbox_aggregate", _TABLE, ["aggregate_type", "aggregate_id"])
    op.create_index("idx_outbox_created_at", _TABLE, ["created_at"])


def downgrade() -> None:
    """Drop the event_outbox table, restoring the pre-migration schema."""
    op.drop_index("idx_outbox_created_at", table_name=_TABLE)
    op.drop_index("idx_outbox_aggregate", table_name=_TABLE)
    op.drop_index("idx_outbox_unpublished", table_name=_TABLE)
    op.drop_table(_TABLE)
