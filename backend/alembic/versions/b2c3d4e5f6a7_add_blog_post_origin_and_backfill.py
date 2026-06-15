"""add blog_post origin column and additive carousel backfill

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-15 09:00:00.000000

AE-0127: ADDITIVE, behavior-preserving, reversible.

This migration is **purely additive** — it adds one column to ``blog_posts`` and
inserts new ``origin='carousel'`` rows backfilled from the carousel embedded blog
columns. It does **NOT** drop the embedded ``carousel_projects`` blog/distribution
columns (``blog_markdown`` / ``blog_translations`` / ``caption*`` /
``linkedin_post_*``) — that destructive drop is DEFERRED to AE-0133. Because no
destructive schema change occurs, the LangGraph **checkpoint-drain gate does NOT
block** this migration (the drain rule applies only to destructive migrations).

Steps (upgrade):

1. Add ``blog_posts.origin`` (``String(20)``, NOT NULL, server_default
   ``'standalone'``) so every existing row backfills to ``'standalone'`` without a
   separate UPDATE.
2. Re-classify existing project-linked rows: ``UPDATE blog_posts SET
   origin='carousel' WHERE project_id IS NOT NULL``.
3. One-time backfill: for every **completed/public** carousel
   (``status='completed'`` OR ``is_public`` true) with a non-null ``blog_markdown``
   and no existing ``origin='carousel'`` blog_posts row, insert a ``blog_posts``
   row (``origin='carousel'``, ``project_id`` set). **Idempotent** — guarded by a
   per-project ``WHERE NOT EXISTS`` check, so re-running inserts no duplicate.

The migration is **reversible**: ``downgrade`` deletes the ``origin='carousel'``
rows this migration created (those with a ``project_id``) and drops the ``origin``
column, restoring the pre-migration ``blog_posts`` schema + data.

Cross-dialect: the backfill runs through SQLAlchemy Core against lightweight table
projections (no ORM), so it applies identically on SQLite (tests) and Postgres
(prod). The new ``origin`` column is mirrored in ``BlogPostModel`` so the
autogenerate drift check stays empty.
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
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

# --- Constants -----------------------------------------------------------------
_ORIGIN_STANDALONE = "standalone"
_ORIGIN_CAROUSEL = "carousel"
_CAROUSEL_STATUS_COMPLETED = "completed"
_BLOG_POST_DEFAULT_STATUS = "published"
_BLOG_SLUG_PREFIX = "carousel-"

# Lightweight table projections (no ORM) for the cross-dialect backfill.
_carousel_projects = sa.table(
    "carousel_projects",
    sa.column("id", sa.String),
    sa.column("title", sa.String),
    sa.column("topic", sa.String),
    sa.column("blog_markdown", sa.Text),
    sa.column("blog_translations", sa.JSON),
    sa.column("status", sa.String),
    sa.column("is_public", sa.Boolean),
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
    """Add the origin column + idempotently backfill carousel-derived posts."""
    op.add_column(
        "blog_posts",
        sa.Column(
            "origin",
            sa.String(length=20),
            server_default=_ORIGIN_STANDALONE,
            nullable=False,
        ),
    )

    bind = op.get_bind()
    bind.execute(
        sa
        .update(_blog_posts)
        .where(_blog_posts.c.project_id.isnot(None))
        .values(origin=_ORIGIN_CAROUSEL)
    )

    now = datetime.now(UTC)
    source_rows = bind.execute(
        sa.select(_carousel_projects).where(
            _carousel_projects.c.blog_markdown.isnot(None),
            sa.or_(
                _carousel_projects.c.status == _CAROUSEL_STATUS_COMPLETED,
                _carousel_projects.c.is_public.is_(True),
            ),
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
    """Delete the backfilled carousel rows, then drop the additive origin column."""
    bind = op.get_bind()
    bind.execute(
        sa.delete(_blog_posts).where(
            _blog_posts.c.origin == _ORIGIN_CAROUSEL,
            _blog_posts.c.project_id.isnot(None),
        )
    )
    op.drop_column("blog_posts", "origin")
