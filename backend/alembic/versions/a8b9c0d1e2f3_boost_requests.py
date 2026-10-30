"""boost requests

Revision ID: a8b9c0d1e2f3
Revises: f9a0b1c2d3e4
Create Date: 2026-10-29

Additive tables for owner-approved Instagram boosts. Idempotent.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "a8b9c0d1e2f3"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None

_REQUESTS = "boost_requests"
_EVENTS = "boost_request_events"
_INDEX = "ix_boost_requests_status_next_attempt"
_OPEN = "status IN ('pending_approval','approved','launching','active')"


def _has_table(name: str) -> bool:
    return bool(sa.inspect(op.get_bind()).has_table(name))


def upgrade() -> None:
    """Create the request and event tables when missing."""
    if not _has_table(_REQUESTS):
        op.create_table(
            _REQUESTS,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("idempotency_key", sa.String(128), nullable=False),
            sa.Column("request_hash", sa.String(64), nullable=False),
            sa.Column("media_id", sa.String(128), nullable=False),
            sa.Column("status", sa.String(24), nullable=False),
            sa.Column("objective", sa.String(24), nullable=False),
            sa.Column("daily_budget_cents", sa.Integer(), nullable=False),
            sa.Column("days", sa.Integer(), nullable=False),
            sa.Column("total_budget_cents", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("audience", sa.JSON(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("decided_by", sa.String(64), nullable=True),
            sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
            sa.Column("permalink", sa.Text(), nullable=True),
            sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("meta_campaign_id", sa.String(64), nullable=True),
            sa.Column("meta_adset_id", sa.String(64), nullable=True),
            sa.Column("meta_creative_id", sa.String(64), nullable=True),
            sa.Column("meta_ad_id", sa.String(64), nullable=True),
            sa.Column("launch_attempts", sa.Integer(), nullable=False),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_insights", sa.JSON(), nullable=True),
            sa.Column("insights_fetched_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_code", sa.String(64), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("idempotency_key"),
        )
        op.create_index(_INDEX, _REQUESTS, ["status", "next_attempt_at"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            sa.text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_boost_requests_media_active "
                f"ON {_REQUESTS} (media_id) WHERE {_OPEN}"
            )
        )
    if _has_table(_EVENTS):
        return
    op.create_table(
        _EVENTS,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("from_status", sa.String(24), nullable=False),
        sa.Column("to_status", sa.String(24), nullable=False),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], [f"{_REQUESTS}.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop the boost tables."""
    if _has_table(_EVENTS):
        op.drop_table(_EVENTS)
    if not _has_table(_REQUESTS):
        return
    if op.get_bind().dialect.name == "postgresql":
        op.execute(sa.text("DROP INDEX IF EXISTS uq_boost_requests_media_active"))
    op.drop_index(_INDEX, table_name=_REQUESTS)
    op.drop_table(_REQUESTS)
