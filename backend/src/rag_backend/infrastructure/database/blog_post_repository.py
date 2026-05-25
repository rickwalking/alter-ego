"""Optimized blog post repository for list queries (PERF-001)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.blog_post import BlogPostModel


class BlogPostRepository:
    """Data access for blog posts with optimized listing."""

    async def list_summaries(
        self,
        db: AsyncSession,
        *,
        status_filter: str | None = None,
        author_id: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BlogPostModel], int]:
        """List blog posts without loading heavy content column when possible."""
        filters = []
        if status_filter:
            filters.append(BlogPostModel.status == status_filter)
        if author_id:
            filters.append(BlogPostModel.author_id == author_id)
        if search:
            pattern = f"%{search.lower()}%"
            filters.append(
                func.lower(BlogPostModel.title).like(pattern)
                | func.lower(BlogPostModel.slug).like(pattern)
            )

        count_query = select(func.count()).select_from(BlogPostModel)
        list_query = select(BlogPostModel)
        for clause in filters:
            count_query = count_query.where(clause)
            list_query = list_query.where(clause)

        list_query = (
            list_query
            .order_by(BlogPostModel.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )

        total_result = await db.execute(count_query)
        total = int(total_result.scalar_one())

        result = await db.execute(list_query)
        return list(result.scalars().all()), total


__all__ = ["BlogPostRepository"]
