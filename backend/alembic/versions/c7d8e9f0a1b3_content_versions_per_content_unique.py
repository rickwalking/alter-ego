"""content_versions unique index per content

Revision ID: c7d8e9f0a1b3
Revises: f7a8b9c0d1e2
Create Date: 2026-10-22

``content_versions`` had a global unique index on
``(content_type, version_number)``, so two carousels could not both have a
version 1. The caption / LinkedIn version history numbers versions per
carousel, so the index becomes unique on
``(content_id, content_type, version_number)``. The old index was stricter, so
existing rows always fit the new one. ``downgrade`` restores the global index
(it fails if two contents now share a number, which is the point of the change).

prod: the deploy does not run alembic, so the same change reaches prod through
the idempotent one-shot ``python -m rag_backend.scripts.content_versions_index
--apply --verify`` that deploy.yml runs after the blog cutover (Pedro's
decision; no manual DDL).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "c7d8e9f0a1b3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None

_TABLE = "content_versions"
_GLOBAL_INDEX = "idx_content_versions_version"
_PER_CONTENT_INDEX = "uq_content_versions_content_version"


def _index_names() -> set[str] | None:
    """The table's index names, or ``None`` when the table does not exist.

    A database stamped past the baseline without the table (the stamped SQLite
    revision tests) has nothing to change.
    """
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(_TABLE):
        return None
    return {str(index["name"]) for index in inspector.get_indexes(_TABLE)}


def upgrade() -> None:
    """Swap the global unique index for the per-content one."""
    names = _index_names()
    if names is None:
        return
    if _GLOBAL_INDEX in names:
        op.drop_index(_GLOBAL_INDEX, table_name=_TABLE)
    if _PER_CONTENT_INDEX in names:
        return
    op.create_index(
        _PER_CONTENT_INDEX,
        _TABLE,
        ["content_id", "content_type", "version_number"],
        unique=True,
    )


def downgrade() -> None:
    """Put the global unique index back."""
    names = _index_names()
    if names is None:
        return
    if _PER_CONTENT_INDEX in names:
        op.drop_index(_PER_CONTENT_INDEX, table_name=_TABLE)
    if _GLOBAL_INDEX in names:
        return
    op.create_index(
        _GLOBAL_INDEX, _TABLE, ["content_type", "version_number"], unique=True
    )
