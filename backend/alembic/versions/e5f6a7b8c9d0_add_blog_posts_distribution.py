"""add blog_posts.distribution JSONB + backfill caption/linkedin (AE-0204)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-17 09:00:00.000000

AE-0204: ADDITIVE, behavior-preserving, reversible.

Gives the Instagram **caption** and the **LinkedIn posts** (``linkedin_post_pt`` /
``linkedin_post_en``) a single canonical home — a new ``blog_posts.distribution``
JSONB column (mirroring the ``blog_posts.content`` JSONB pattern, ADR-0006) — so the
embedded ``carousel_projects`` distribution columns can later be dropped (AE-0205)
without data loss or a broken IG/LinkedIn publish.

This migration is **purely additive** — it adds one column to ``blog_posts`` and
backfills it from the embedded carousel columns. It does **NOT** drop the embedded
``carousel_projects`` columns (``caption`` / ``linkedin_post_pt`` /
``linkedin_post_en``) — that destructive drop is DEFERRED to AE-0205. Because no
destructive schema change occurs, the LangGraph checkpoint-drain gate does NOT
block this migration (the drain rule applies only to destructive migrations).

Steps (upgrade):

1. Add ``blog_posts.distribution`` (``JSON``, NOT NULL, server_default ``'{}'``) so
   every existing row backfills to an empty object without a separate UPDATE.
2. Backfill: for every ``origin='carousel'`` ``blog_posts`` row, copy the linked
   carousel project's ``caption`` / ``linkedin_post_pt`` / ``linkedin_post_en``
   (joined on ``project_id``) into ``distribution``. **Idempotent** — re-running
   re-derives the same payload from the same source columns, overwriting with an
   identical value.

``downgrade`` drops the ``distribution`` column, restoring the pre-migration
schema. No data is lost on downgrade: the embedded ``carousel_projects`` columns
(this migration's backfill source) are never mutated, so the source of truth is
still intact for a re-``upgrade``.

Cross-dialect: the backfill runs through SQLAlchemy Core against lightweight table
projections (no ORM), so it applies identically on SQLite (tests) and Postgres
(prod). The new ``distribution`` column is mirrored in ``BlogPostModel`` so the
autogenerate drift check stays empty.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None

# --- Constants -----------------------------------------------------------------
_ORIGIN_CAROUSEL = "carousel"
_DISTRIBUTION_DEFAULT = "{}"
_CAPTION_KEY = "caption"
_LINKEDIN_PT_KEY = "linkedin_post_pt"
_LINKEDIN_EN_KEY = "linkedin_post_en"

# Lightweight table projections (no ORM) for the cross-dialect backfill.
_carousel_projects = sa.table(
    "carousel_projects",
    sa.column("id", sa.String),
    sa.column("caption", sa.Text),
    sa.column("linkedin_post_pt", sa.Text),
    sa.column("linkedin_post_en", sa.Text),
)
_blog_posts = sa.table(
    "blog_posts",
    sa.column("id", sa.String),
    sa.column("project_id", sa.String),
    sa.column("origin", sa.String),
    sa.column("distribution", sa.JSON),
)


def _distribution_payload(row: Mapping[str, object]) -> dict[str, object]:
    """Build the canonical ``{caption, linkedin_post_pt, linkedin_post_en}`` body."""
    return {
        _CAPTION_KEY: row["caption"],
        _LINKEDIN_PT_KEY: row["linkedin_post_pt"],
        _LINKEDIN_EN_KEY: row["linkedin_post_en"],
    }


def upgrade() -> None:
    """Add the distribution column + backfill it from the embedded carousel copy."""
    op.add_column(
        "blog_posts",
        sa.Column(
            "distribution",
            sa.JSON(),
            server_default=_DISTRIBUTION_DEFAULT,
            nullable=False,
        ),
    )

    bind = op.get_bind()
    carousel_rows = bind.execute(
        sa.select(_carousel_projects)
    ).fetchall()
    source_by_id = {
        str(row._mapping["id"]): cast("Mapping[str, object]", row._mapping)
        for row in carousel_rows
    }

    blog_rows = bind.execute(
        sa.select(_blog_posts.c.id, _blog_posts.c.project_id).where(
            _blog_posts.c.origin == _ORIGIN_CAROUSEL,
            _blog_posts.c.project_id.isnot(None),
        )
    ).fetchall()

    for blog_row in blog_rows:
        mapping = blog_row._mapping
        source = source_by_id.get(str(mapping["project_id"]))
        if source is None:
            continue
        bind.execute(
            sa
            .update(_blog_posts)
            .where(_blog_posts.c.id == mapping["id"])
            .values(distribution=_distribution_payload(source))
        )


def downgrade() -> None:
    """Drop the distribution column (the embedded source columns are untouched)."""
    op.drop_column("blog_posts", "distribution")
