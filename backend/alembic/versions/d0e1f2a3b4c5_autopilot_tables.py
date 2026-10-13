"""autopilot_tables

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-10-13

AE-0350: ADDITIVE. Creates the four autopilot tables and drops nothing, so
the LangGraph checkpoint-drain gate does not apply (no existing table is
altered). ``downgrade`` drops the new tables.

``carousel_project_id`` is VARCHAR(36) to match ``carousel_projects.id``.
Run and topic primary keys are UUIDs. JSON columns are JSONB on PostgreSQL
and JSON on other dialects (SQLite tests).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None

_RUNS = "autopilot_runs"
_TOPICS = "topic_candidates"
_CREDENTIALS = "integration_credentials"
_TELEGRAM = "telegram_updates"
_INDEX_STATE_UPDATED = "idx_autopilot_runs_state_updated_at"


def _json() -> sa.JSON:
    """JSON on SQLite, JSONB on PostgreSQL."""
    return sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    """Create the four autopilot tables and the run state index."""
    op.create_table(
        _TOPICS,
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("angle", sa.Text(), nullable=False),
        sa.Column("why_viral", sa.Text(), nullable=False),
        sa.Column("audience", sa.Text(), nullable=False),
        sa.Column("niche", sa.Text(), nullable=False),
        sa.Column("brief", sa.Text(), nullable=False),
        sa.Column("sources", _json(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("signal_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("signal_hash", name="uq_topic_candidates_signal_hash"),
    )
    op.create_table(
        _RUNS,
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "carousel_project_id",
            sa.String(length=36),
            sa.ForeignKey(
                "carousel_projects.id",
                name="fk_autopilot_runs_carousel_project_id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.Column(
            "topic_candidate_id",
            sa.Uuid(),
            sa.ForeignKey(
                "topic_candidates.id",
                name="fk_autopilot_runs_topic_candidate_id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("state_reason", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("telegram_message_ids", _json(), nullable=False),
        sa.Column("ig_container_id", sa.String(length=128), nullable=True),
        sa.Column("ig_post_id", sa.String(length=128), nullable=True),
        sa.Column("ig_permalink", sa.Text(), nullable=True),
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
            nullable=False,
        ),
        sa.UniqueConstraint(
            "carousel_project_id",
            name="uq_autopilot_runs_carousel_project_id",
        ),
    )
    op.create_index(
        _INDEX_STATE_UPDATED,
        _RUNS,
        ["state", "updated_at"],
    )
    op.create_table(
        _CREDENTIALS,
        sa.Column("provider", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("encrypted_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        _TELEGRAM,
        sa.Column("update_id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Drop the four autopilot tables, restoring the previous schema."""
    op.drop_table(_TELEGRAM)
    op.drop_table(_CREDENTIALS)
    op.drop_index(_INDEX_STATE_UPDATED, table_name=_RUNS)
    op.drop_table(_RUNS)
    op.drop_table(_TOPICS)
