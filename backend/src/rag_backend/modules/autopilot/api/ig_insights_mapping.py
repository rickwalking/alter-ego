"""Domain report to ``GET /api/autopilot/ig-insights``."""

from __future__ import annotations

from typing import cast

from rag_backend.modules.autopilot.api.ig_insights_schemas import (
    IgAccountBaselineModel,
    IgInsightsResponse,
    IgMediaBoostStateModel,
    IgMediaInsightsItemModel,
    IgMediaMetrics,
    IgMediaRatesModel,
    MediaTypeName,
    ProductTypeName,
)
from rag_backend.modules.autopilot.domain.ig_media import (
    IgAccountBaseline,
    IgInsightItem,
    IgInsightsReport,
    IgMediaRates,
    OpenBoost,
)
from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.ig_media_constants import MEDIA_TYPES, PRODUCT_TYPES


def ig_insights_response(report: IgInsightsReport) -> IgInsightsResponse:
    """Copy the report into the API model. Unknown media types are dropped."""
    return IgInsightsResponse(
        items=[
            _item(row) for row in report.items if row.media.media_type in MEDIA_TYPES
        ],
        baseline={key: _baseline(value) for key, value in report.baseline.items()},
        next_until=report.next_until,
        configured=report.configured,
        list_truncated=report.list_truncated,
        generated_at=report.generated_at,
    )


def _item(row: IgInsightItem) -> IgMediaInsightsItemModel:
    product = row.media.media_product_type
    return IgMediaInsightsItemModel(
        media_id=row.media.media_id,
        media_type=cast(MediaTypeName, row.media.media_type),
        media_product_type=_product(product),
        permalink=row.media.permalink,
        caption_excerpt=row.media.caption_excerpt,
        timestamp=row.media.posted_at,
        age_hours=row.age_hours,
        carousel_project_id=_project_id(row),
        topic=None if row.project is None else row.project.topic,
        like_count=row.media.like_count,
        comments_count=row.media.comments_count,
        metrics=_metrics(row.metrics),
        rates=_rates(row.rates),
        fetched_at=row.fetched_at,
        stale=row.stale,
        boost=_boost(row.boost),
    )


def _project_id(row: IgInsightItem) -> str | None:
    if row.project is None:
        return None
    return row.project.carousel_project_id


def _product(value: str | None) -> ProductTypeName | None:
    if value not in PRODUCT_TYPES:
        return None
    return cast(ProductTypeName, value)


def _metrics(metrics: InsightMetrics) -> IgMediaMetrics:
    return IgMediaMetrics(
        views=metrics.views,
        reach=metrics.reach,
        likes=metrics.likes,
        comments=metrics.comments,
        saved=metrics.saved,
        shares=metrics.shares,
        follows=metrics.follows,
        profile_visits=metrics.profile_visits,
        total_interactions=metrics.total_interactions,
        avg_watch_time_ms=metrics.avg_watch_time_ms,
        total_watch_time_ms=metrics.total_watch_time_ms,
    )


def _rates(rates: IgMediaRates) -> IgMediaRatesModel:
    return IgMediaRatesModel(
        shares_per_100_views=rates.shares_per_100_views,
        saves_per_100_reach=rates.saves_per_100_reach,
        follows_per_1000_reach=rates.follows_per_1000_reach,
        engagement_rate=rates.engagement_rate,
    )


def _baseline(value: IgAccountBaseline) -> IgAccountBaselineModel:
    return IgAccountBaselineModel(
        sample_size=value.sample_size,
        median_reach=value.median_reach,
        median_shares_per_100_views=value.median_shares_per_100_views,
        median_saves_per_100_reach=value.median_saves_per_100_reach,
        median_follows_per_1000_reach=value.median_follows_per_1000_reach,
        median_engagement_rate=value.median_engagement_rate,
    )


def _boost(boost: OpenBoost | None) -> IgMediaBoostStateModel | None:
    if boost is None:
        return None
    return IgMediaBoostStateModel(request_id=boost.request_id, status=boost.status)


__all__ = ["ig_insights_response"]
