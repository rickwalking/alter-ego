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
columns.

PR #106 review: ``topic_candidates`` also gains the scout v3 ``pov_format`` and
``slide_count`` (NULL = the autopilot default). Folded into this revision to
keep ``c2d3e4f5a6b7`` the single head; safe because the revision is idempotent
and prod applies the SQL by hand.

Idempotent (AE-0371 review): prod has no ``alembic_version`` table and the SQL
was applied by hand, so each column is added only when missing and dropped only
when present.
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
_POV_FORMAT_LENGTH = 30


_COLUMNS: tuple[tuple[str, str, sa.types.TypeEngine[object]], ...] = (
    (_TOPICS, "content_mode", sa.String(_MODE_LENGTH)),
    (_TOPICS, "thesis_draft", sa.String(_THESIS_LENGTH)),
    (_RUNS, "pov_thesis", sa.String(_THESIS_LENGTH)),
    (_TOPICS, "pov_format", sa.String(_POV_FORMAT_LENGTH)),
    (_TOPICS, "slide_count", sa.Integer()),
)


def _has_column(table: str, name: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(table)
    return any(column["name"] == name for column in columns)


def upgrade() -> None:
    """Add the POV columns (if missing)."""
    for table, name, column_type in _COLUMNS:
        if _has_column(table, name):
            continue
        op.add_column(table, sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    """Drop the POV columns (only those present)."""
    for table, name, _column_type in reversed(_COLUMNS):
        if not _has_column(table, name):
            continue
        op.drop_column(table, name)
