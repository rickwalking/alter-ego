"""Optimized blog post repository for list queries (PERF-001)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.blog_post import BlogPostModel


@dataclass(frozen=True)
class _BlogPostListQuery:
    """Query filters for listing blog post summaries."""

    status_filter: str | None = None
    author_id: str | None = None
    search: str | None = None
    limit: int = 50
    offset: int = 0


class BlogPostRepository:
    """Data access for blog posts with optimized listing."""

    @staticmethod
    async def list_summaries(
        db: AsyncSession,
        query_params: _BlogPostListQuery = _BlogPostListQuery(),
    ) -> tuple[list[BlogPostModel], int]:
        """List blog posts without loading heavy content column when possible."""
        filters = []
        if query_params.status_filter:
            filters.append(BlogPostModel.status == query_params.status_filter)
        if query_params.author_id:
            filters.append(BlogPostModel.author_id == query_params.author_id)
        if query_params.search:
            pattern = f"%{query_params.search.lower()}%"
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
            .limit(query_params.limit)
            .offset(query_params.offset)
        )

        total_result = await db.execute(count_query)
        total = int(total_result.scalar_one())

        result = await db.execute(list_query)
        return list(result.scalars().all()), total


__all__ = ["BlogPostRepository"]
