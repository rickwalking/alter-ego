"""Request and response bodies of the Reels and repost routes (ADR-0031)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from rag_backend.modules.autopilot.repost_constants import (
    HOOK_DURATION_DEFAULT,
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=False)


class CoverRef(_Strict):
    """``{"asset_id": "<uuid>"}``."""

    asset_id: UUID


class WindowBody(_Strict):
    """Publish no earlier than ``earliest`` and no later than ``latest``."""

    earliest: datetime
    latest: datetime


class RepostCreate(_Strict):
    """``POST /repost`` body. Range rules live in the domain."""

    media_id: str = Field(min_length=1, max_length=64)
    caption: str = Field(max_length=4000)
    hook_text: str | None = Field(default=None, max_length=1000)
    hook_duration_s: float = HOOK_DURATION_DEFAULT
    trim_start_s: float = 0.0
    trim_end_s: float | None = None
    cover: CoverRef | None = None
    collaborators: list[str] | None = Field(default=None, max_length=20)
    share_to_feed: bool = True
    reason: str = Field(max_length=2000)
    score: float | None = Field(default=None, allow_inf_nan=False)
    publish_window: WindowBody | None = None


class RepostAccepted(BaseModel):
    """The 202 body."""

    id: UUID
    status: str
    media_id: str
    permalink: str | None
    preview_url: str
    expires_at: datetime
    created_at: datetime


class RepostView(BaseModel):
    """``GET /repost/{id}`` and each item of ``GET /reposts``."""

    id: UUID
    status: str
    media_id: str
    permalink: str | None
    new_media_id: str | None
    new_permalink: str | None
    cover_used: str | None
    publish_at: datetime | None
    preview_url: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    expires_at: datetime
    approved_at: datetime | None
    published_at: datetime | None


class RepostListView(BaseModel):
    """Newest first."""

    items: list[RepostView]


class ReelMetricsView(BaseModel):
    """Counts from the latest insight snapshot."""

    views: int | None
    reach: int | None
    likes: int | None
    comments: int | None
    saved: int | None
    shares: int | None
    follows: int | None
    avg_watch_time_ms: int | None
    total_watch_time_ms: int | None


class ReelRatesView(BaseModel):
    """Derived rates; null when an input is missing."""

    shares_per_100_views: float | None
    saves_per_100_reach: float | None
    follows_per_1000_reach: float | None
    engagement_rate: float | None
    avg_watch_ratio: float | None


class LastRepostView(BaseModel):
    """The newest repost of the Reel."""

    repost_id: UUID
    status: str
    created_at: datetime
    published_at: datetime | None


class ReelView(BaseModel):
    """One Reel the scout may repost."""

    media_id: str
    shortcode: str | None
    permalink: str | None
    media_product_type: str | None
    timestamp: datetime
    age_days: int
    caption: str | None
    collaborators: list[str]
    duration_s: float | None
    thumbnail_url: str | None
    video_url: str | None
    video_url_expires_at: datetime | None
    metrics: ReelMetricsView
    rates: ReelRatesView
    stale: bool
    last_repost: LastRepostView | None


class ReelsBaselineView(BaseModel):
    """Medians over the Reels in the age window."""

    median_views: float | None
    median_shares_per_100_views: float | None
    median_engagement_rate: float | None


class ReelsView(BaseModel):
    """``GET /reels``."""

    items: list[ReelView]
    baseline: ReelsBaselineView
    next_cursor: str | None
    generated_at: datetime


__all__ = [
    "CoverRef",
    "LastRepostView",
    "ReelMetricsView",
    "ReelRatesView",
    "ReelView",
    "ReelsBaselineView",
    "ReelsView",
    "RepostAccepted",
    "RepostCreate",
    "RepostListView",
    "RepostView",
    "WindowBody",
]
