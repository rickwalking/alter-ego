"""Alembic migration for Phase 3 workflow and collaboration tables."""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_phase3_workflow_collaboration"
down_revision = "0001_add_blog_posts_and_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_audit_log",
        sa.Column("id", sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column("event_id", sa.String(36), nullable=False, unique=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.String(36), nullable=False),
        sa.Column("aggregate_type", sa.String(50), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("payload", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("stream_entry_id", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_audit_aggregate", "workflow_audit_log", ["aggregate_type", "aggregate_id"])
    op.create_index("idx_audit_event_type", "workflow_audit_log", ["event_type"])
    op.create_index("idx_audit_created_at", "workflow_audit_log", ["created_at"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="unread"),
        sa.Column("content_id", sa.String(36), nullable=True),
        sa.Column("content_type", sa.String(50), nullable=True),
        sa.Column("metadata", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("email_sent", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_notifications_user_status", "notifications", ["user_id", "status"])
    op.create_index("idx_notifications_deadline", "notifications", ["deadline_at"])
    op.create_index("idx_notifications_content", "notifications", ["content_type", "content_id"])

    op.create_table(
        "content_locks",
        sa.Column("id", sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column("content_id", sa.String(36), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("user_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_content_locks_content",
        "content_locks",
        ["content_type", "content_id"],
        unique=True,
    )
    op.create_index("idx_content_locks_expires", "content_locks", ["expires_at"])

    op.add_column(
        "blog_posts",
        sa.Column("lock_version", sa.Integer, nullable=False, server_default="1"),
    )
    op.add_column(
        "carousel_projects",
        sa.Column("lock_version", sa.Integer, nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("carousel_projects", "lock_version")
    op.drop_column("blog_posts", "lock_version")
    op.drop_index("idx_content_locks_expires", table_name="content_locks")
    op.drop_index("idx_content_locks_content", table_name="content_locks")
    op.drop_table("content_locks")
    op.drop_index("idx_notifications_content", table_name="notifications")
    op.drop_index("idx_notifications_deadline", table_name="notifications")
    op.drop_index("idx_notifications_user_status", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("idx_audit_created_at", table_name="workflow_audit_log")
    op.drop_index("idx_audit_event_type", table_name="workflow_audit_log")
    op.drop_index("idx_audit_aggregate", table_name="workflow_audit_log")
    op.drop_table("workflow_audit_log")
