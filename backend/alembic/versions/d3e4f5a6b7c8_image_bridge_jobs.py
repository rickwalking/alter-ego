"""image bridge jobs

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-10-15

AE-0393 (ADR-0022): ADDITIVE. One new table, ``image_bridge_jobs``: one row
per Grok Bot image job. ``image_bytes`` holds the callback image until the
waiter reads it once and nulls it. No existing table or column is altered or
dropped. ``downgrade`` drops the table and its index.

Idempotent like the AE-0371 revisions: prod has no ``alembic_version`` and the
backend creates missing tables at startup, so upgrade skips an existing table
or index and downgrade skips missing ones.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None

_JOBS = "image_bridge_jobs"
_INDEX = "ix_image_bridge_jobs_status_expires_at"
_STATUS_LENGTH = 16
_SIZE_LENGTH = 16
_TOKEN_SHA256_LENGTH = 64
_ERROR_CODE_LENGTH = 128


def _inspector() -> sa.engine.reflection.Inspector:
    return sa.inspect(op.get_bind())


def _has_table() -> bool:
    return bool(_inspector().has_table(_JOBS))


def _has_index() -> bool:
    return any(index["name"] == _INDEX for index in _inspector().get_indexes(_JOBS))


def upgrade() -> None:
    """Create the bridge job table and its sweep index (each if missing)."""
    if not _has_table():
        op.create_table(
            _JOBS,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("status", sa.String(_STATUS_LENGTH), nullable=False),
            sa.Column("size", sa.String(_SIZE_LENGTH), nullable=False),
            sa.Column("token_sha256", sa.String(_TOKEN_SHA256_LENGTH), nullable=False),
            sa.Column("image_bytes", sa.LargeBinary(), nullable=True),
            sa.Column("error_code", sa.String(_ERROR_CODE_LENGTH), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index():
        op.create_index(_INDEX, _JOBS, ["status", "expires_at"])


def downgrade() -> None:
    """Drop the bridge job table and its index (each if present)."""
    if not _has_table():
        return
    if _has_index():
        op.drop_index(_INDEX, table_name=_JOBS)
    op.drop_table(_JOBS)
