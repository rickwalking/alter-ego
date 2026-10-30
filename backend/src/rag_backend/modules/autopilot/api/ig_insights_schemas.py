"""Response models for ``GET /api/autopilot/ig-insights``."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from rag_backend.modules.autopilot.ig_media_constants import CAPTION_EXCERPT_LENGTH

MediaTypeName = Literal["IMAGE", "CAROUSEL_ALBUM", "VIDEO"]
ProductTypeName = Literal["FEED", "REELS"]


class IgMediaMetrics(BaseModel):
    """Graph metrics. Null means the metric was not returned."""

    views: int | None = None
    reach: int | None = None
    likes: int | None = None
    comments: int | None = None
    saved: int | None = None
    shares: int | None = None
    follows: int | None = None
    profile_visits: int | None = None
    total_interactions: int | None = None
    avg_watch_time_ms: int | None = None
    total_watch_time_ms: int | None = None


class IgMediaRatesModel(BaseModel):
    """Derived rates. Null when an input is null or the divisor is zero."""

    shares_per_100_views: float | None = None
    saves_per_100_reach: float | None = None
    follows_per_1000_reach: float | None = None
    engagement_rate: float | None = None


class IgMediaBoostStateModel(BaseModel):
    """Latest non-terminal boost request. Null until a request exists."""

    request_id: str
    status: str


class IgMediaInsightsItemModel(BaseModel):
    """One account media row."""

    media_id: str
    media_type: MediaTypeName
    media_product_type: ProductTypeName | None
    permalink: str | None
    caption_excerpt: str | None = Field(default=None, max_length=CAPTION_EXCERPT_LENGTH)
    timestamp: datetime
    age_hours: float
    carousel_project_id: str | None = None
    topic: str | None = None
    like_count: int | None = None
    comments_count: int | None = None
    metrics: IgMediaMetrics
    rates: IgMediaRatesModel
    fetched_at: datetime | None
    stale: bool
    boost: IgMediaBoostStateModel | None = None


class IgAccountBaselineModel(BaseModel):
    """Medians for posts aged between 72 hours and 30 days."""

    sample_size: int
    median_reach: float | None
    median_shares_per_100_views: float | None
    median_saves_per_100_reach: float | None
    median_follows_per_1000_reach: float | None
    median_engagement_rate: float | None


class IgInsightsResponse(BaseModel):
    """Account media, newest first, plus per-type baselines."""

    items: list[IgMediaInsightsItemModel]
    baseline: dict[str, IgAccountBaselineModel]
    next_until: datetime | None
    configured: bool
    list_truncated: bool
    generated_at: datetime


__all__ = ["IgInsightsResponse"]
