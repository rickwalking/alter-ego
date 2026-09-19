"""Public-visibility predicate for anonymous blog reads (AE-0347).

The carousel dual-write stamps every ``origin='carousel'`` blog row as
``published`` the moment the workflow composes it, while the carousel itself only
becomes public on the explicit site release (``is_public=True``). The public blog
surface therefore must also require the parent carousel to be public, or a
never-released carousel's blog leaks through ``/public/blog-posts``.
"""

from __future__ import annotations

from sqlalchemy import ColumnElement, and_, or_, select

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


__all__ = ["BLOG_ORIGIN_CAROUSEL", "public_blog_visibility_clause"]
