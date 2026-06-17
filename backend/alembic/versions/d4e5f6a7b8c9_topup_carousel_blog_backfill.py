"""top-up carousel-blog backfill for completeness (AE-0163)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-16 09:00:00.000000

AE-0163: ADDITIVE, behavior-preserving, data-only (no schema change).

The carousel-blog READ path (``project_carousel_blog`` / ``resolve_blog_body`` +
the 404 gate) is converted in AE-0163 to source the body + the 404 signal SOLELY
from the ``origin='carousel'`` ``blog_posts`` row, dropping the embedded
``carousel_projects.blog_markdown`` read fallback. For that to stay byte-identical,
**every** carousel that has a non-null ``blog_markdown`` must have a matching
``origin='carousel'`` row — otherwise a live read could flip a legacy 200 into a
404 (the de-risking precondition for the deferred AE-0162 column drop).

AE-0127 (``b2c3d4e5f6a7``) backfilled rows only for carousels that were
``status='completed'`` OR ``is_public`` at migration time. A carousel whose
``blog_markdown`` was set but which was neither completed nor public at that moment
— and that has had no blog write since (the AE-0163 repository dual-write covers
every subsequent write) — would lack a row. This migration closes that residual
gap: it inserts an ``origin='carousel'`` row for **any** carousel with a non-null
``blog_markdown`` that still has no carousel-origin row, regardless of
status/visibility, in the EXACT AE-0127 row shape (``carousel-{id}`` slug, ``title
= title or topic or "Carousel {id}"``, ``excerpt`` NULL, ``status='published'``,
``content = {"markdown": ..., "translations": ...}``).

**Idempotent** — guarded by a per-project ``WHERE NOT EXISTS`` check, so re-running
inserts no duplicate and rows already created by AE-0127 (or by the AE-0163
dual-write) are left untouched.

``downgrade`` is intentionally a **no-op**: the inserted rows are purely-additive
data (they introduce no schema change and break nothing if retained), and they are
indistinguishable by slug from the AE-0127-inserted rows, so the AE-0127 downgrade
— which deletes every ``carousel-%`` slug row before dropping the ``origin`` column
— already removes them on a full downgrade chain. A no-op downgrade therefore
restores the pre-migration state without data loss.

Cross-dialect: the backfill runs through SQLAlchemy Core against lightweight table
projections (no ORM), so it applies identically on SQLite (tests) and Postgres
(prod). No schema change is made, so the autogenerate drift check stays empty.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import cast

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None

# --- Constants -----------------------------------------------------------------
_ORIGIN_CAROUSEL = "carousel"
_BLOG_POST_DEFAULT_STATUS = "published"
_BLOG_SLUG_PREFIX = "carousel-"

# Lightweight table projections (no ORM) for the cross-dialect backfill — same
# shape as the AE-0127 migration so the inserted rows are byte-identical.
_carousel_projects = sa.table(
    "carousel_projects",
    sa.column("id", sa.String),
    sa.column("title", sa.String),
    sa.column("topic", sa.String),
    sa.column("blog_markdown", sa.Text),
    sa.column("blog_translations", sa.JSON),
)
_blog_posts = sa.table(
    "blog_posts",
    sa.column("id", sa.String),
    sa.column("project_id", sa.String),
    sa.column("origin", sa.String),
    sa.column("title", sa.String),
    sa.column("slug", sa.String),
    sa.column("status", sa.String),
    sa.column("content", sa.JSON),
    sa.column("editor_comments", sa.JSON),
    sa.column("version_history", sa.JSON),
    sa.column("sources", sa.JSON),
    sa.column("citations", sa.JSON),
    sa.column("ai_suggestions", sa.JSON),
    sa.column("ai_generation_metadata", sa.JSON),
    sa.column("ai_disclosure_label", sa.String),
    sa.column("keywords", sa.JSON),
    sa.column("view_count", sa.Integer),
    sa.column("like_count", sa.Integer),
    sa.column("comment_count", sa.Integer),
    sa.column("share_count", sa.Integer),
    sa.column("lock_version", sa.Integer),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)


def _carousel_blog_title(row: Mapping[str, object]) -> str:
    """Derive a non-empty blog title from a carousel row (title → topic → id)."""
    return str(row["title"] or row["topic"] or f"Carousel {row['id']}")


def _carousel_blog_content(row: Mapping[str, object]) -> dict[str, object]:
    """Build the JSON content body from the carousel blog markdown + translations."""
    translations = row["blog_translations"]
    if isinstance(translations, str):
        translations = json.loads(translations)
    return {
        "markdown": row["blog_markdown"],
        "translations": translations if isinstance(translations, dict) else {},
    }


def _backfill_row_values(row: Mapping[str, object], now: datetime) -> dict[str, object]:
    """Assemble the full NOT-NULL column set for one backfilled blog_posts row."""
    return {
        "id": str(uuid.uuid4()),
        "project_id": row["id"],
        "origin": _ORIGIN_CAROUSEL,
        "title": _carousel_blog_title(row),
        "slug": f"{_BLOG_SLUG_PREFIX}{row['id']}",
        "status": _BLOG_POST_DEFAULT_STATUS,
        "content": _carousel_blog_content(row),
        "editor_comments": [],
        "version_history": [],
        "sources": [],
        "citations": [],
        "ai_suggestions": [],
        "ai_generation_metadata": {},
        "ai_disclosure_label": "none",
        "keywords": [],
        "view_count": 0,
        "like_count": 0,
        "comment_count": 0,
        "share_count": 0,
        "lock_version": 1,
        "created_at": now,
        "updated_at": now,
    }


def upgrade() -> None:
    """Idempotently insert a carousel-origin row for every body-bearing carousel."""
    bind = op.get_bind()
    now = datetime.now(UTC)
    source_rows = bind.execute(
        sa.select(_carousel_projects).where(
            _carousel_projects.c.blog_markdown.isnot(None),
        )
    ).fetchall()

    for source_row in source_rows:
        row = cast("Mapping[str, object]", source_row._mapping)
        exists = bind.execute(
            sa.select(_blog_posts.c.id).where(
                _blog_posts.c.project_id == row["id"],
                _blog_posts.c.origin == _ORIGIN_CAROUSEL,
            )
        ).first()
        if exists is not None:
            continue
        bind.execute(sa.insert(_blog_posts).values(**_backfill_row_values(row, now)))


def downgrade() -> None:
    """No-op: the additive top-up rows are removed by the AE-0127 downgrade.

    See the module docstring — the inserted rows share the AE-0127 ``carousel-%``
    slug scheme and are deleted by that earlier migration's downgrade on a full
    chain, so this downgrade intentionally does nothing (no schema change to undo,
    no data loss).
    """
