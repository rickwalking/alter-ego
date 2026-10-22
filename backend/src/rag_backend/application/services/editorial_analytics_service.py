"""Editorial analytics aggregation (UI-027 backend)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.persona_rubric import (
    RubricEvaluationScoreModel,
)

AD_HOC_EVALUATION_CONTENT_ID = str(UUID(int=0))
QUALITY_SCORE_DECIMALS = 1


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
        quality_average, quality_count = await self._content_quality_score(db)

        return {
            "total_posts": len(posts),
            "published_this_week": published_week,
            "published_this_month": published_month,
            "content_velocity_per_week": published_week,
            "status_breakdown": status_counts,
            "average_views": avg_views,
            "pending_review": in_review,
            "draft_count": drafts,
            "quality_score_average": quality_average,
            "quality_score_count": quality_count,
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
    async def _content_quality_score(db: AsyncSession) -> tuple[float | None, int]:
        """Average ``overall_score`` of content rubric scores, and how many.

        Ad-hoc evaluations of pasted text carry the nil content id and are not a
        score of any content, so they are left out. Without a content score the
        average is ``None``: the dashboard shows "no data", never a stand-in.
        """
        query = select(
            func.avg(RubricEvaluationScoreModel.overall_score),
            func.count(RubricEvaluationScoreModel.id),
        ).where(RubricEvaluationScoreModel.content_id != AD_HOC_EVALUATION_CONTENT_ID)
        average, count = (await db.execute(query)).one()
        if not count:
            return None, 0
        return round(float(average), QUALITY_SCORE_DECIMALS), int(count)


__all__ = ["EditorialAnalyticsService"]
