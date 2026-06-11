"""Editorial analytics aggregation (UI-027 backend)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.blog_post import BlogPostModel


class EditorialAnalyticsService:
    """Aggregates content velocity and quality metrics for dashboard."""

    async def get_summary(
        self, db: AsyncSession, author_id: str | None = None
    ) -> dict[str, object]:
        """Return editorial analytics summary."""
        base = select(BlogPostModel)
        if author_id:
            base = base.where(BlogPostModel.author_id == author_id)

        result = await db.execute(base)
        posts = list(result.scalars().all())

        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        published_week = sum(
            1
            for p in posts
            if p.published_at and p.published_at.replace(tzinfo=UTC) >= week_ago
        )
        published_month = sum(
            1
            for p in posts
            if p.published_at and p.published_at.replace(tzinfo=UTC) >= month_ago
        )

        status_counts: dict[str, int] = {}
        for post in posts:
            status_counts[post.status] = status_counts.get(post.status, 0) + 1

        avg_views = 0
        if posts:
            avg_views = sum(p.view_count for p in posts) // len(posts)

        in_review = status_counts.get("under_review", 0)
        drafts = status_counts.get("draft", 0)

        return {
            "total_posts": len(posts),
            "published_this_week": published_week,
            "published_this_month": published_month,
            "content_velocity_per_week": published_week,
            "status_breakdown": status_counts,
            "average_views": avg_views,
            "pending_review": in_review,
            "draft_count": drafts,
            "quality_score_average": self._estimate_quality_score(posts),
        }

    @staticmethod
    async def get_velocity_by_week(
        db: AsyncSession, weeks: int = 8, author_id: str | None = None
    ) -> list[dict[str, object]]:
        """Return weekly publish counts for charting."""
        query = select(BlogPostModel).where(BlogPostModel.published_at.isnot(None))
        if author_id:
            query = query.where(BlogPostModel.author_id == author_id)
        result = await db.execute(query)
        posts = list(result.scalars().all())

        now = datetime.now(UTC)
        buckets: list[dict[str, object]] = []
        for week_idx in range(weeks - 1, -1, -1):
            start = now - timedelta(days=(week_idx + 1) * 7)
            end = now - timedelta(days=week_idx * 7)
            count = sum(
                1
                for p in posts
                if p.published_at and start <= p.published_at.replace(tzinfo=UTC) < end
            )
            buckets.append({
                "week_start": start.date().isoformat(),
                "published_count": count,
            })
        return buckets

    @staticmethod
    def _estimate_quality_score(posts: list[BlogPostModel]) -> float:
        if not posts:
            return 0.0
        scores: list[float] = []
        for post in posts:
            metadata = post.ai_generation_metadata or {}
            if isinstance(metadata, dict):
                score = metadata.get("quality_score")
                if isinstance(score, (int, float)):
                    scores.append(float(score))
        if not scores:
            published_ratio = sum(1 for p in posts if p.status == "published") / len(
                posts
            )
            return round(published_ratio * 100, 1)
        return round(sum(scores) / len(scores), 1)


__all__ = ["EditorialAnalyticsService"]
