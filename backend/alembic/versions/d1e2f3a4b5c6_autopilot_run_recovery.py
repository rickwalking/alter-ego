"""autopilot run recovery columns and manual publish ledger

Revision ID: d1e2f3a4b5c6
Revises: c8d9e0f1a2b3
Create Date: 2026-10-14

AE-0348 QA r1: ADDITIVE. ``autopilot_runs`` gains a start-attempt counter
(the existing ``attempts`` column stays the publish-attempt counter), the
owner's queued rework intent, the lock version recorded at escalation, and
``publish_claimed_at``, the compare-and-set claim that keeps the worker and
the manual publish route from both calling Graph for one run.
``instagram_manual_publishes`` persists the post id of owner-triggered
publishes for carousels that have no autopilot run and is the row lock
that keeps two manual publishes from both calling Graph.
``autopilot_notify_cursor`` is the Telegram notifier's oldest-first position
in the outbox, so no undelivered notice is skipped. No existing column
is altered or dropped, so the LangGraph checkpoint-drain rule does not
apply. ``downgrade`` drops what ``upgrade`` added.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d1e2f3a4b5c6"
down_revision = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None

_RUNS = "autopilot_runs"
_MANUAL = "instagram_manual_publishes"
_START_ATTEMPTS = "start_attempts"
_REWORK_PHASE = "rework_phase"
_REWORK_FEEDBACK = "rework_feedback"
_ESCALATED_VERSION = "escalated_version"
_PUBLISH_CLAIMED_AT = "publish_claimed_at"
_PHASE_LENGTH = 32
_STATE_LENGTH = 32
_ID_LENGTH = 36
_IG_ID_LENGTH = 128
_FK_PROJECT = "fk_instagram_manual_publishes_carousel_project"
_CURSOR = "autopilot_notify_cursor"
_CURSOR_NAME_LENGTH = 32


def upgrade() -> None:
    """Add the run recovery columns and the manual publish ledger."""
    op.add_column(
        _RUNS,
        sa.Column(
            _START_ATTEMPTS,
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        _RUNS, sa.Column(_REWORK_PHASE, sa.String(_PHASE_LENGTH), nullable=True)
    )
    op.add_column(_RUNS, sa.Column(_REWORK_FEEDBACK, sa.Text(), nullable=True))
    op.add_column(_RUNS, sa.Column(_ESCALATED_VERSION, sa.Integer(), nullable=True))
    op.add_column(
        _RUNS,
        sa.Column(_PUBLISH_CLAIMED_AT, sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        _MANUAL,
        sa.Column(
            "carousel_project_id",
            sa.String(_ID_LENGTH),
            sa.ForeignKey(
                "carousel_projects.id",
                name=_FK_PROJECT,
                ondelete="CASCADE",
            ),
            primary_key=True,
        ),
        sa.Column("state", sa.String(_STATE_LENGTH), nullable=False),
        sa.Column("ig_post_id", sa.String(_IG_ID_LENGTH), nullable=True),
        sa.Column("ig_permalink", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        _CURSOR,
        sa.Column("name", sa.String(_CURSOR_NAME_LENGTH), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_id", sa.String(_ID_LENGTH), nullable=False),
    )


def downgrade() -> None:
    """Drop the manual publish ledger and the run recovery columns."""
    op.drop_table(_CURSOR)
    op.drop_table(_MANUAL)
    op.drop_column(_RUNS, _PUBLISH_CLAIMED_AT)
    op.drop_column(_RUNS, _ESCALATED_VERSION)
    op.drop_column(_RUNS, _REWORK_FEEDBACK)
    op.drop_column(_RUNS, _REWORK_PHASE)
    op.drop_column(_RUNS, _START_ATTEMPTS)
