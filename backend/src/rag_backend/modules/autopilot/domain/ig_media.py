"""Account media, rates and baselines for the autopilot insights read.

Pure values. Graph and SQL live in infrastructure. A missing metric stays
``None`` and never becomes zero.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from rag_backend.modules.autopilot.domain.insights import InsightMetrics, shares_per_100
from rag_backend.modules.autopilot.ig_media_constants import (
    AGE_HOURS_DIGITS,
    BASELINE_MAX_AGE_DAYS,
    BASELINE_MIN_AGE_HOURS,
    BASELINE_ROW_CAP,
    ENGAGEMENT_RATE_DIGITS,
    FOLLOWS_PER_REACH_BASE,
    METRICS_FEED,
    METRICS_REELS,
    METRICS_SHARED,
    PRODUCT_FEED,
    PRODUCT_REELS,
    RATE_DIGITS,
    SAVES_PER_REACH_BASE,
    SECONDS_PER_HOUR,
)


@dataclass(frozen=True, kw_only=True)
class IgMedia:
    """One Instagram media object, caption clipped."""

    media_id: str
    media_type: str
    media_product_type: str | None
    permalink: str | None
    caption_excerpt: str | None
    posted_at: datetime
    like_count: int | None
    comments_count: int | None


@dataclass(frozen=True, kw_only=True)
class MediaListCommand:
    """How far back the Graph walk should go."""

    since: datetime


@dataclass(frozen=True, kw_only=True)
class MediaListResult:
    """Media seen on the walk, newest first, plus whether the page cap stopped it."""

    items: tuple[IgMedia, ...]
    truncated: bool


@dataclass(frozen=True, kw_only=True)
class TimeWindow:
    """Inclusive start, exclusive end."""

    start: datetime
    end: datetime


@dataclass(frozen=True, kw_only=True)
class MediaProject:
    """Backend carousel linked to a media id, when one exists."""

    carousel_project_id: str | None
    topic: str | None


@dataclass(frozen=True, kw_only=True)
class BaselineSample:
    """One settled post used for the account median."""

    product_type: str
    metrics: InsightMetrics


@dataclass(frozen=True, kw_only=True)
class IgMediaRates:
    """Derived rates. Null when a numerator is null or a denominator is null or 0."""

    shares_per_100_views: float | None
    saves_per_100_reach: float | None
    follows_per_1000_reach: float | None
    engagement_rate: float | None


@dataclass(frozen=True, kw_only=True)
class IgAccountBaseline:
    """Medians for one product type. ``sample_size`` counts posts, not filled rates."""

    sample_size: int
    median_reach: float | None
    median_shares_per_100_views: float | None
    median_saves_per_100_reach: float | None
    median_follows_per_1000_reach: float | None
    median_engagement_rate: float | None


@dataclass(frozen=True, kw_only=True)
class OpenBoost:
    """Latest non-terminal boost request for one media id."""

    request_id: str
    status: str


@dataclass(frozen=True, kw_only=True)
class IgInsightItem:
    """One row of the autopilot insights read."""

    media: IgMedia
    metrics: InsightMetrics
    rates: IgMediaRates
    fetched_at: datetime | None
    stale: bool
    age_hours: float
    project: MediaProject | None
    boost: OpenBoost | None = None


@dataclass(frozen=True, kw_only=True)
class IgInsightsReport:
    """The read the boost bot scores from."""

    items: tuple[IgInsightItem, ...]
    baseline: dict[str, IgAccountBaseline]
    next_until: datetime | None
    configured: bool
    list_truncated: bool
    generated_at: datetime


@dataclass(frozen=True, kw_only=True)
class IgInsightsRequest:
    """Raw query values, before defaults and the 90-day check."""

    since: datetime | None
    until: datetime | None
    limit: int
    media_type: str | None
    product_type: str | None
    refresh: bool


@dataclass(frozen=True, kw_only=True)
class ResolvedIgQuery:
    """Query the service can run."""

    since: datetime
    until: datetime
    limit: int
    media_type: str | None
    product_type: str | None
    refresh: bool


class MediaListGateway(Protocol):
    """Reads the account's media list from Graph."""

    async def list_media(self, command: MediaListCommand) -> MediaListResult:
        """Newest first, down to ``command.since`` or the page cap."""
        ...


class IgMediaStore(Protocol):
    """Cached media rows, project links and baseline samples."""

    async def list_is_fresh(self, now: datetime) -> bool:
        """True when the newest ``listed_at`` is inside the list TTL."""
        ...

    async def upsert(self, items: Sequence[IgMedia], listed_at: datetime) -> None:
        """Insert or replace the walked rows."""
        ...

    async def in_window(self, window: TimeWindow) -> list[IgMedia]:
        """Rows with ``posted_at`` in the window, newest first."""
        ...

    async def projects(self, media_ids: Sequence[str]) -> dict[str, MediaProject]:
        """Carousel id and topic for media this backend published."""
        ...

    async def baseline_samples(self, window: TimeWindow) -> list[BaselineSample]:
        """Settled posts, capped per product type."""
        ...

    async def commit(self) -> None:
        """Commit upserts and snapshot writes on this session."""
        ...


def metrics_for(product_type: str | None) -> tuple[str, ...]:
    """Graph metric names for one product type. Unknown types use the shared set."""
    if product_type == PRODUCT_REELS:
        return METRICS_REELS
    if product_type == PRODUCT_FEED:
        return METRICS_FEED
    return METRICS_SHARED


def rates_for(metrics: InsightMetrics) -> IgMediaRates:
    """The four rates. Each is null when its inputs are missing or the divisor is 0."""
    return IgMediaRates(
        shares_per_100_views=shares_per_100(metrics.shares, metrics.views),
        saves_per_100_reach=_per(metrics.saved, metrics.reach, SAVES_PER_REACH_BASE),
        follows_per_1000_reach=_per(
            metrics.follows, metrics.reach, FOLLOWS_PER_REACH_BASE
        ),
        engagement_rate=_ratio(metrics.total_interactions, metrics.reach),
    )


def age_hours(posted_at: datetime, now: datetime) -> float:
    """Hours since the post, rounded to one decimal."""
    elapsed = (now - posted_at).total_seconds() / SECONDS_PER_HOUR
    return round(elapsed, AGE_HOURS_DIGITS)


def baselines(samples: Sequence[BaselineSample]) -> dict[str, IgAccountBaseline]:
    """One baseline per product type, including an empty sample."""
    return {
        PRODUCT_FEED: _baseline(_of_type(samples, PRODUCT_FEED)),
        PRODUCT_REELS: _baseline(_of_type(samples, PRODUCT_REELS)),
    }


def baseline_window(now: datetime) -> TimeWindow:
    """Settled posts that still describe the account."""
    return TimeWindow(
        start=now - timedelta(days=BASELINE_MAX_AGE_DAYS),
        end=now - timedelta(hours=BASELINE_MIN_AGE_HOURS),
    )


def empty_baselines() -> dict[str, IgAccountBaseline]:
    """Both keys, zero samples. Used when Graph is not configured."""
    return baselines(())


def _per(numerator: int | None, denominator: int | None, scale: int) -> float | None:
    if numerator is None or not denominator:
        return None
    return round(scale * numerator / denominator, RATE_DIGITS)


def _ratio(numerator: int | None, denominator: int | None) -> float | None:
    if numerator is None or not denominator:
        return None
    return round(numerator / denominator, ENGAGEMENT_RATE_DIGITS)


def _of_type(samples: Sequence[BaselineSample], product: str) -> list[BaselineSample]:
    matched = [sample for sample in samples if sample.product_type == product]
    return matched[:BASELINE_ROW_CAP]


def _baseline(samples: Sequence[BaselineSample]) -> IgAccountBaseline:
    rates = [rates_for(sample.metrics) for sample in samples]
    reaches = [
        float(sample.metrics.reach) for sample in samples if sample.metrics.reach
    ]
    return IgAccountBaseline(
        sample_size=len(samples),
        median_reach=_median(reaches),
        median_shares_per_100_views=_median(_share_rates(rates)),
        median_saves_per_100_reach=_median(_save_rates(rates)),
        median_follows_per_1000_reach=_median(_follow_rates(rates)),
        median_engagement_rate=_median(_engagement_rates(rates)),
    )


def _share_rates(rates: Sequence[IgMediaRates]) -> list[float]:
    return _numbers(rate.shares_per_100_views for rate in rates)


def _save_rates(rates: Sequence[IgMediaRates]) -> list[float]:
    return _numbers(rate.saves_per_100_reach for rate in rates)


def _follow_rates(rates: Sequence[IgMediaRates]) -> list[float]:
    return _numbers(rate.follows_per_1000_reach for rate in rates)


def _engagement_rates(rates: Sequence[IgMediaRates]) -> list[float]:
    return _numbers(rate.engagement_rate for rate in rates)


def _numbers(values: Iterable[float | None]) -> list[float]:
    return [value for value in values if value is not None]


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


__all__ = [
    "BaselineSample",
    "IgAccountBaseline",
    "IgInsightItem",
    "IgInsightsReport",
    "IgInsightsRequest",
    "IgMedia",
    "IgMediaRates",
    "IgMediaStore",
    "MediaListCommand",
    "MediaListGateway",
    "MediaListResult",
    "MediaProject",
    "OpenBoost",
    "ResolvedIgQuery",
    "TimeWindow",
    "age_hours",
    "baseline_window",
    "baselines",
    "empty_baselines",
    "metrics_for",
    "rates_for",
]
