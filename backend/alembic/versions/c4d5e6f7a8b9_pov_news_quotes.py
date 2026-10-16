"""pov_news quotes and sources

Revision ID: c4d5e6f7a8b9
Revises: a0e4f0a4b4c4
Create Date: 2026-10-16

AE-0406 (ADR-0023): ADDITIVE. ``topic_candidates`` gains ``quotes`` (the scout's
verified quotes of a ``pov_news`` topic); ``carousel_projects`` gains
``pov_quotes`` (the same quotes, carried onto the carousel) and ``pov_sources``
(the topic's sources in order, for the caption footer). Every column is
nullable JSON; no existing column is altered or dropped. ``content_mode`` is a
plain ``String(20)`` with no enum or check constraint, so ``pov_news`` needs no
change there. ``downgrade`` drops the three columns.

Idempotent like the AE-0371 revisions: prod has no ``alembic_version`` table and
applies the SQL by hand, so each column is added only when missing and dropped
only when present.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "c4d5e6f7a8b9"
down_revision = "a0e4f0a4b4c4"
branch_labels = None
depends_on = None

_TOPICS = "topic_candidates"
_PROJECTS = "carousel_projects"


def _columns() -> tuple[tuple[str, str, sa.types.TypeEngine[object]], ...]:
    return (
        (_TOPICS, "quotes", sa.JSON().with_variant(JSONB(), "postgresql")),
        (_PROJECTS, "pov_quotes", sa.JSON()),
        (_PROJECTS, "pov_sources", sa.JSON()),
    )


def _has_column(table: str, name: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(table)
    return any(column["name"] == name for column in columns)


def upgrade() -> None:
    """Add the pov_news columns (if missing)."""
    for table, name, column_type in _columns():
        if _has_column(table, name):
            continue
        op.add_column(table, sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    """Drop the pov_news columns (only those present)."""
    for table, name, _column_type in reversed(_columns()):
        if not _has_column(table, name):
            continue
        op.drop_column(table, name)
