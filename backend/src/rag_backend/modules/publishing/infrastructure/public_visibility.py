"""Public-visibility predicate for anonymous blog reads (AE-0347).

The carousel dual-write stamps every ``origin='carousel'`` blog row as
``published`` the moment the workflow composes it, while the carousel itself only
becomes public on the explicit site release (``is_public=True``). The public blog
surface therefore must also require the parent carousel to be public, or a
never-released carousel's blog leaks through ``/public/blog-posts``.
"""

from __future__ import annotations

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.blog_post import BlogPostOrigin, BlogPostStatus
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

BLOG_ORIGIN_CAROUSEL = BlogPostOrigin.CAROUSEL.value


def public_blog_visibility_clause() -> ColumnElement[bool]:
    """Rows readable anonymously: published AND (not carousel OR carousel public)."""
    parent_is_public = (
        select(CarouselProjectModel.id)
        .where(CarouselProjectModel.id == BlogPostModel.project_id)
        .where(CarouselProjectModel.is_public.is_(True))
        .exists()
    )
    return and_(
        BlogPostModel.status == BlogPostStatus.PUBLISHED.value,
        or_(BlogPostModel.origin != BLOG_ORIGIN_CAROUSEL, parent_is_public),
    )


async def public_blog_post_ids(
    session: AsyncSession,
    post_ids: list[str],
) -> frozenset[str]:
    """Return the subset of ``post_ids`` that anonymous readers can see (AE-0411).

    Same rule as the public API (:func:`public_blog_visibility_clause`), so the
    dashboard can tell a live post from a carousel-linked row that is stored
    ``published`` but whose carousel has not been released yet.
    """
    if not post_ids:
        return frozenset()
    query = select(BlogPostModel.id).where(
        BlogPostModel.id.in_(post_ids),
        public_blog_visibility_clause(),
    )
    result = await session.execute(query)
    return frozenset(str(post_id) for post_id in result.scalars().all())


__all__ = [
    "BLOG_ORIGIN_CAROUSEL",
    "public_blog_post_ids",
    "public_blog_visibility_clause",
]
