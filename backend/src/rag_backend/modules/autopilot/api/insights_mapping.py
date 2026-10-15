"""Domain report -> ``GET /api/instagram/insights`` response (AE-0378)."""

from __future__ import annotations

from rag_backend.modules.autopilot.api.schemas import (
    InstagramInsightsResponse,
    InstagramPostInsightsItem,
)
from rag_backend.modules.autopilot.domain.insights import (
    InsightsReport,
    PostInsightsRow,
)


def insights_response(
    report: InsightsReport, *, configured: bool
) -> InstagramInsightsResponse:
    """Map the domain report to the API response."""
    return InstagramInsightsResponse(
        items=[_item(row) for row in report.rows],
        follows_total=report.follows_total,
        follows_per_post=report.follows_per_post,
        shares_per_100_views=report.shares_per_100_views,
        configured=configured,
    )


def _item(row: PostInsightsRow) -> InstagramPostInsightsItem:
    metrics = row.metrics
    return InstagramPostInsightsItem(
        media_id=row.post.media_id,
        carousel_project_id=row.post.carousel_project_id,
        permalink=row.post.permalink,
        topic=row.post.topic,
        views=metrics.views,
        reach=metrics.reach,
        saved=metrics.saved,
        shares=metrics.shares,
        follows=metrics.follows,
        profile_visits=metrics.profile_visits,
        total_interactions=metrics.total_interactions,
        shares_per_100_views=row.shares_per_100_views,
        fetched_at=row.fetched_at,
        stale=row.stale,
    )


__all__ = ["insights_response"]
