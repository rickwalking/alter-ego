"""Carousel-blog dual-write: blog_posts (origin='carousel') the SOLE writer (AE-0163).

Behavior-preserving predecessor to the destructive column drop (AE-0162). Every
carousel writer that used to treat the embedded ``carousel_projects.blog_markdown``
/ ``blog_translations`` columns as the source of truth funnels through the carousel
repository's ``create_project`` / ``update_project``; this module is the single
chokepoint that, on each such write, **upserts the canonical
``origin='carousel'`` ``blog_posts`` row** from the carousel's blog body so that
row — not the embedded column — becomes the source of truth the read path consumes.

The upserted row is **byte-identical in shape** to the AE-0127 backfill migration
(``b2c3d4e5f6a7``): same generated ``carousel-{project_id}`` slug, same
``title = title or topic or "Carousel {id}"``, ``excerpt`` NULL, ``status``
``'published'``, and ``content = {"markdown": blog_markdown, "translations": ...}``.
This keeps the projection + 404 semantics byte-identical (AE-0125 safety net) while
removing the embedded columns' role as the WRITE source of truth.

The upsert is **idempotent**: it reuses the existing ``origin='carousel'`` row for
the project when present (created by AE-0127 or a prior dual-write) and only mutates
its derived fields, so repeated writes never insert a duplicate.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.blog_post import BlogPostOrigin, BlogPostStatus
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.database.distribution_home import build_distribution
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

# Generated slug scheme — identical to the AE-0127 backfill migration so the
# upserted row is indistinguishable from a migration-backfilled row.
_BLOG_SLUG_PREFIX = "carousel-"
# JSON content keys — identical to the AE-0127 backfill body shape.
_CONTENT_MARKDOWN_KEY = "markdown"
_CONTENT_TRANSLATIONS_KEY = "translations"


def _carousel_blog_title(project: CarouselProject) -> str:
    """Derive the non-empty blog title (title → topic → id) — AE-0127 identical."""
    return project.title or project.topic or f"Carousel {project.id}"


def _carousel_blog_content(project: CarouselProject) -> dict[str, object]:
    """Build the JSON content body from the carousel blog body — AE-0127 identical."""
    translations = project.blog_translations
    return {
        _CONTENT_MARKDOWN_KEY: project.blog_markdown,
        _CONTENT_TRANSLATIONS_KEY: dict(translations) if translations else {},
    }


async def sync_carousel_blog_post(
    session: AsyncSession,
    project: CarouselProject,
) -> None:
    """Upsert the canonical ``origin='carousel'`` blog_posts row for ``project``.

    No-op when the carousel carries no embedded blog body (``blog_markdown`` is
    ``None``): the read path's 404 gate keys on the row's presence, and AE-0127
    only ever backfilled rows for non-null ``blog_markdown`` carousels, so writing
    a row for a body-less carousel would flip a legacy 404 into a 200.

    Idempotent: reuses the project's existing carousel-origin row when present
    (created by AE-0127 or a prior dual-write) and refreshes its derived fields;
    otherwise inserts a new row in the AE-0127 shape. The row is flushed (not
    committed) so it shares the caller's single transaction (the repository
    commits once).
    """
    if project.blog_markdown is None:
        return

    row = await _existing_carousel_row(session, str(project.id))
    title = _carousel_blog_title(project)
    content = _carousel_blog_content(project)
    # AE-0204: mirror the distribution copy (caption + LinkedIn posts) into the
    # canonical ``blog_posts.distribution`` home on the same row, in the same
    # transaction, so the canonical home stays the source of truth every reader
    # consumes (the embedded carousel columns are retained but read-dead).
    distribution = build_distribution(project)
    if row is not None:
        row.title = title
        row.content = content
        row.distribution = distribution
        await session.flush()
        return

    session.add(
        BlogPostModel.from_entity({
            "id": str(uuid.uuid4()),
            "project_id": str(project.id),
            "origin": BlogPostOrigin.CAROUSEL.value,
            "title": title,
            "slug": f"{_BLOG_SLUG_PREFIX}{project.id}",
            "status": BlogPostStatus.PUBLISHED.value,
            "content": content,
            "distribution": distribution,
        })
    )
    await session.flush()


async def _existing_carousel_row(
    session: AsyncSession,
    project_id: str,
) -> BlogPostModel | None:
    """Return the project's existing ``origin='carousel'`` row, or ``None``."""
    query = select(BlogPostModel).where(
        BlogPostModel.project_id == project_id,
        BlogPostModel.origin == BlogPostOrigin.CAROUSEL.value,
    )
    result = await session.execute(query)
    return result.scalars().first()


__all__ = ["sync_carousel_blog_post"]
