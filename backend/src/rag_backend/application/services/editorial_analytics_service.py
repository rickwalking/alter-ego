"""Editorial analytics: blog-status summary fields (legacy UI-027 backend).

The channel-pluggable publishing counts and velocity live in
``modules/publishing/infrastructure/publishing_channels.py`` (strictly
type-checked); this legacy service only loads the blog rows for the
blog-specific status fields of the analytics summary.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.blog_post import BlogPostModel


class EditorialAnalyticsService:
    """Blog-status counts for the dashboard analytics summary."""

    @staticmethod
    async def get_summary(
        db: AsyncSession, author_id: str | None = None
    ) -> dict[str, object]:
        """Return the blog-specific summary fields (no channel data)."""
        posts = await EditorialAnalyticsService._posts(db, author_id)
        status_counts = _status_counts(posts)
        return {
            "total_posts": len(posts),
            "status_breakdown": status_counts,
            "pending_review": status_counts.get("under_review", 0),
            "draft_count": status_counts.get("draft", 0),
        }

    @staticmethod
    async def _posts(db: AsyncSession, author_id: str | None) -> list[BlogPostModel]:
        """Every blog post, scoped to the author when given."""
        query = select(BlogPostModel)
        if author_id:
            query = query.where(BlogPostModel.author_id == author_id)
        result = await db.execute(query)
        return list(result.scalars().all())


def _status_counts(posts: list[BlogPostModel]) -> dict[str, int]:
    """Histogram of blog-post statuses."""
    counts: dict[str, int] = {}
    for post in posts:
        counts[post.status] = counts.get(post.status, 0) + 1
    return counts


__all__ = ["EditorialAnalyticsService"]
