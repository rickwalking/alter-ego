"""Lean public blog-post schemas (AE-0297, ADR-0013).

The public surface is an explicit **allow-list**: every serialized field is
mapped by hand (never ``from_orm``/``model_validate`` over the full model), so
a future column added to ``blog_posts`` can never leak publicly by default.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from rag_backend.modules.publishing import BlogPostModel

PUBLIC_BLOG_DEFAULT_LIMIT = 20
PUBLIC_BLOG_MAX_LIMIT = 50


class PublicBlogListParams(BaseModel):
    """Pagination for the public blog listing (status is server-forced)."""

    limit: int = Field(PUBLIC_BLOG_DEFAULT_LIMIT, ge=1, le=PUBLIC_BLOG_MAX_LIMIT)
    offset: int = Field(0, ge=0)


# Internal field names that must NEVER appear anywhere in a public payload
# (recursively — including nested JSON). Guarded by a security regression test.
PUBLIC_BLOG_POST_EXCLUDED_FIELDS: frozenset[str] = frozenset({
    "status",
    "author_id",
    "reviewer_id",
    "editor_comments",
    "version_history",
    "ai_suggestions",
    "ai_generation_metadata",
    "lock_version",
    "distribution",
    "sources",
    "citations",
    "view_count",
})


class PublicBlogPostSummary(BaseModel):
    """Public listing item — lean allow-list projection of a published post."""

    id: UUID
    slug: str
    title: str
    excerpt: str | None = None
    featured_image_url: str | None = None
    published_at: datetime | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    keywords: list[str] = Field(default_factory=list)
    canonical_url: str | None = None
    origin: str
    project_id: UUID | None = None


class PublicBlogPostResponse(PublicBlogPostSummary):
    """Public detail — summary plus the rendered content body."""

    content: dict[str, object] = Field(default_factory=dict)


class PublicBlogPostListResponse(BaseModel):
    """Public listing envelope."""

    items: list[PublicBlogPostSummary]
    total: int
    limit: int
    offset: int


def to_public_summary(post: "BlogPostModel") -> PublicBlogPostSummary:
    """Build the lean summary by explicit field mapping (allow-list)."""
    return PublicBlogPostSummary.model_validate({
        "id": post.id,
        "slug": post.slug,
        "title": post.title,
        "excerpt": post.excerpt,
        "featured_image_url": post.featured_image_url,
        "published_at": post.published_at,
        "meta_title": post.meta_title,
        "meta_description": post.meta_description,
        "keywords": list(post.keywords or []),
        "canonical_url": post.canonical_url,
        "origin": post.origin,
        "project_id": post.project_id,
    })


def to_public_detail(post: "BlogPostModel") -> PublicBlogPostResponse:
    """Build the lean detail by explicit field mapping (allow-list)."""
    summary = to_public_summary(post)
    return PublicBlogPostResponse(
        **summary.model_dump(),
        content=dict(post.content or {}),
    )
