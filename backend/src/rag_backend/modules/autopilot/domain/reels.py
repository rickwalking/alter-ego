"""Reels the scout may repost: values, rates, sort order and baseline. No I/O."""

from __future__ import annotations

import statistics
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from rag_backend.modules.autopilot.domain.ig_media import IgMediaRates, rates_for
from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.reels_constants import (
    CDN_EXPIRY_PARAM,
    HEX_BASE,
    MS_PER_SECOND,
    SECONDS_PER_DAY,
    SORT_SHARES_RATE,
    SORT_TIMESTAMP,
    SORT_VIEWS,
    WATCH_RATIO_DIGITS,
)


@dataclass(frozen=True, kw_only=True)
class ReelMedia:
    """One Reel from the Graph media edge. URLs expire."""

    media_id: str
    shortcode: str | None
    permalink: str | None
    product_type: str | None
    posted_at: datetime
    caption: str | None
    video_url: str | None
    thumbnail_url: str | None


@dataclass(frozen=True, kw_only=True)
class ReelFacts:
    """Facts Graph does not list: duration (ffprobe) and collaborators."""

    media_id: str
    duration_s: float | None
    collaborators: tuple[str, ...]
    probed_at: datetime


@dataclass(frozen=True, kw_only=True)
class LastRepost:
    """The newest repost of a Reel."""

    repost_id: UUID
    status: str
    created_at: datetime
    published_at: datetime | None


@dataclass(frozen=True, kw_only=True)
class ReelRates:
    """The four account rates plus the share of the Reel watched on average."""

    base: IgMediaRates
    avg_watch_ratio: float | None


@dataclass(frozen=True, kw_only=True)
class ReelItem:
    """One row of ``GET /reels``."""

    media: ReelMedia
    facts: ReelFacts | None
    metrics: InsightMetrics
    rates: ReelRates
    stale: bool
    age_days: int
    last_repost: LastRepost | None


@dataclass(frozen=True, kw_only=True)
class ReelsBaseline:
    """Medians over the Reels in the age window."""

    median_views: float | None
    median_shares_per_100_views: float | None
    median_engagement_rate: float | None


def age_days(posted_at: datetime, now: datetime) -> int:
    """Whole days since the Reel was published."""
    return int((now - posted_at).total_seconds() // SECONDS_PER_DAY)


def reel_rates(metrics: InsightMetrics, duration_s: float | None) -> ReelRates:
    """Account rates, and average watch time over duration (null when unknown)."""
    return ReelRates(
        base=rates_for(metrics),
        avg_watch_ratio=watch_ratio(metrics.avg_watch_time_ms, duration_s),
    )


def watch_ratio(avg_watch_ms: int | None, duration_s: float | None) -> float | None:
    """``avg_watch_time / duration``; null without both or with a zero duration."""
    if avg_watch_ms is None or not duration_s:
        return None
    return round(avg_watch_ms / MS_PER_SECOND / duration_s, WATCH_RATIO_DIGITS)


def _views(item: ReelItem) -> float:
    return float(item.metrics.views) if item.metrics.views is not None else -1.0


def _shares_rate(item: ReelItem) -> float:
    rate = item.rates.base.shares_per_100_views
    return rate if rate is not None else -1.0


def _timestamp(item: ReelItem) -> float:
    return item.media.posted_at.timestamp()


_SORT_KEYS: dict[str, Callable[[ReelItem], float]] = {
    SORT_VIEWS: _views,
    SORT_SHARES_RATE: _shares_rate,
    SORT_TIMESTAMP: _timestamp,
}


def sort_items(items: Sequence[ReelItem], sort: str) -> list[ReelItem]:
    """Best first; unknown metrics last; ties newest first, then by id."""
    key = _SORT_KEYS.get(sort, _views)
    return sorted(
        items,
        key=lambda item: (-key(item), -_timestamp(item), item.media.media_id),
    )


def baseline(items: Sequence[ReelItem]) -> ReelsBaseline:
    """Medians of the filled values; null when none is filled."""
    return ReelsBaseline(
        median_views=_median_of(i.metrics.views for i in items),
        median_shares_per_100_views=_median_of(
            i.rates.base.shares_per_100_views for i in items
        ),
        median_engagement_rate=_median_of(i.rates.base.engagement_rate for i in items),
    )


def cdn_expiry(url: str | None) -> datetime | None:
    """The ``oe`` (hex epoch) expiry of an Instagram CDN URL, if present."""
    if not url:
        return None
    values = parse_qs(urlsplit(url).query).get(CDN_EXPIRY_PARAM)
    if not values:
        return None
    try:
        return datetime.fromtimestamp(int(values[0], HEX_BASE), tz=UTC)
    except (ValueError, OverflowError, OSError):
        return None


def _median_of(values: Iterable[float | None]) -> float | None:
    known = [float(value) for value in values if value is not None]
    return float(statistics.median(known)) if known else None


__all__ = [
    "LastRepost",
    "ReelFacts",
    "ReelItem",
    "ReelMedia",
    "ReelRates",
    "ReelsBaseline",
    "age_days",
    "baseline",
    "cdn_expiry",
    "reel_rates",
    "sort_items",
    "watch_ratio",
]
