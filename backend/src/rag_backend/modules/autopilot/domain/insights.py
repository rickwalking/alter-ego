"""Per-post Instagram insights and the dashboard KPIs (ADR-0021 D11).

Pure values and rules: when a snapshot is due, and the plan's Section-13
ratios (follows per post, shares per 100 views). Every metric is optional:
the Graph API may omit one, and an omitted metric is never estimated.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol

from rag_backend.modules.autopilot.insights_constants import (
    CHANNEL_INSTAGRAM,
    INSIGHT_METRICS,
    INSIGHTS_TTL_HOURS,
    METRIC_AVG_WATCH_TIME,
    METRIC_COMMENTS,
    METRIC_FOLLOWS,
    METRIC_LIKES,
    METRIC_PROFILE_VISITS,
    METRIC_REACH,
    METRIC_SAVED,
    METRIC_SHARES,
    METRIC_TOTAL_INTERACTIONS,
    METRIC_TOTAL_WATCH_TIME,
    METRIC_VIEWS,
    SHARES_PER_VIEWS_BASE,
)


def _unknown_connector() -> InsightsConnector:
    """The connector block before the service fills the real one in."""
    return InsightsConnector(
        channel=CHANNEL_INSTAGRAM,
        configured=False,
        last_sync_at=None,
        stale=False,
        error=None,
    )


@dataclass(frozen=True, kw_only=True)
class InsightMetrics:
    """One post's lifetime metrics; ``None`` = not returned by Graph."""

    views: int | None = None
    reach: int | None = None
    saved: int | None = None
    shares: int | None = None
    follows: int | None = None
    profile_visits: int | None = None
    total_interactions: int | None = None
    likes: int | None = None
    comments: int | None = None
    avg_watch_time_ms: int | None = None
    total_watch_time_ms: int | None = None

    @classmethod
    def from_values(cls, values: Mapping[str, int]) -> InsightMetrics:
        """Build from Graph metric names; unknown names are ignored."""
        return cls(
            views=values.get(METRIC_VIEWS),
            reach=values.get(METRIC_REACH),
            saved=values.get(METRIC_SAVED),
            shares=values.get(METRIC_SHARES),
            follows=values.get(METRIC_FOLLOWS),
            profile_visits=values.get(METRIC_PROFILE_VISITS),
            total_interactions=values.get(METRIC_TOTAL_INTERACTIONS),
            likes=values.get(METRIC_LIKES),
            comments=values.get(METRIC_COMMENTS),
            avg_watch_time_ms=values.get(METRIC_AVG_WATCH_TIME),
            total_watch_time_ms=values.get(METRIC_TOTAL_WATCH_TIME),
        )


@dataclass(frozen=True, kw_only=True)
class PublishedPost:
    """A carousel the autopilot or the manual route published."""

    media_id: str
    carousel_project_id: str | None = None
    permalink: str | None = None
    topic: str | None = None


def dashboard_metrics() -> frozenset[str]:
    """Metric names the dashboard route fetches and is allowed to overwrite."""
    return frozenset(INSIGHT_METRICS)


@dataclass(frozen=True, kw_only=True)
class InsightSnapshot:
    """The last metrics read for one media id."""

    media_id: str
    metrics: InsightMetrics
    fetched_at: datetime
    written: frozenset[str] = field(default_factory=dashboard_metrics)


@dataclass(frozen=True, kw_only=True)
class PostInsightsRow:
    """One dashboard row: the post, its last metrics and whether they are old."""

    post: PublishedPost
    metrics: InsightMetrics
    fetched_at: datetime | None
    stale: bool

    @property
    def shares_per_100_views(self) -> float | None:
        """Shares per 100 views, or None when either is unknown."""
        return shares_per_100(self.metrics.shares, self.metrics.views)


@dataclass(frozen=True, kw_only=True)
class InsightsConnector:
    """Connector health: its name, last sync and refresh error, if any."""

    channel: str
    configured: bool
    last_sync_at: datetime | None
    stale: bool
    error: str | None


@dataclass(frozen=True, kw_only=True)
class InsightsReport:
    """Rows (newest first) and the KPI ratios over the rows that report them."""

    rows: tuple[PostInsightsRow, ...]
    follows_total: int | None
    follows_per_post: float | None
    shares_per_100_views: float | None
    connector: InsightsConnector = field(default_factory=_unknown_connector)


@dataclass(frozen=True, kw_only=True)
class ConnectorStatusQuery:
    """Inputs for :func:`connector_status`."""

    channel: str
    configured: bool
    rows: Sequence[PostInsightsRow]
    now: datetime
    refresh_error: str | None = None


def connector_status(query: ConnectorStatusQuery) -> InsightsConnector:
    """The connector block for one request's rows.

    ``last_sync_at`` is the newest ``fetched_at`` over the rows; the connector
    is stale when that sync is older than the TTL (a connector that never
    synced has nothing outdated to flag yet).
    """
    synced = [row.fetched_at for row in query.rows if row.fetched_at is not None]
    last_sync = max(synced) if synced else None
    stale = last_sync is not None and query.now - last_sync >= timedelta(
        hours=INSIGHTS_TTL_HOURS
    )
    return InsightsConnector(
        channel=query.channel,
        configured=query.configured,
        last_sync_at=last_sync,
        stale=stale,
        error=query.refresh_error,
    )


def is_due(snapshot: InsightSnapshot | None, now: datetime) -> bool:
    """True when there is no snapshot or it is older than the TTL."""
    if snapshot is None:
        return True
    return now - snapshot.fetched_at >= timedelta(hours=INSIGHTS_TTL_HOURS)


def shares_per_100(shares: int | None, views: int | None) -> float | None:
    """``100 * shares / views``; None without both or with no views."""
    if shares is None or not views:
        return None
    return round(SHARES_PER_VIEWS_BASE * shares / views, 2)


def build_report(
    rows: Sequence[PostInsightsRow], *, connector: InsightsConnector | None = None
) -> InsightsReport:
    """The KPI ratios, computed only from posts that report the metric."""
    follows = [r.metrics.follows for r in rows if r.metrics.follows is not None]
    pairs = [
        (r.metrics.shares, r.metrics.views)
        for r in rows
        if r.metrics.shares is not None and r.metrics.views
    ]
    total_follows = sum(follows) if follows else None
    return InsightsReport(
        rows=tuple(rows),
        follows_total=total_follows,
        follows_per_post=round(sum(follows) / len(follows), 2) if follows else None,
        shares_per_100_views=shares_per_100(
            sum(s for s, _ in pairs) if pairs else None,
            sum(v or 0 for _, v in pairs),
        ),
        connector=connector or _unknown_connector(),
    )


class InsightsGateway(Protocol):
    """Reads one post's metrics from the Graph API."""

    async def media_insights(
        self, media_id: str, metrics: tuple[str, ...] = INSIGHT_METRICS
    ) -> InsightMetrics:
        """Raise ``InstagramCallError`` when Graph cannot answer."""
        ...


class InsightsStore(Protocol):
    """Published posts and their stored snapshots."""

    async def published_posts(self, limit: int) -> list[PublishedPost]:
        """The newest published posts, one per media id."""
        ...

    async def snapshots(self, media_ids: Sequence[str]) -> dict[str, InsightSnapshot]:
        """The stored snapshot per media id (absent ids are missing)."""
        ...

    async def save(self, snapshot: InsightSnapshot) -> None:
        """Replace the media id's snapshot."""
        ...

    async def commit(self) -> None:
        """Commit the saved snapshots."""
        ...


__all__ = [
    "ConnectorStatusQuery",
    "InsightMetrics",
    "InsightSnapshot",
    "InsightsConnector",
    "InsightsGateway",
    "InsightsReport",
    "InsightsStore",
    "PostInsightsRow",
    "PublishedPost",
    "build_report",
    "connector_status",
    "dashboard_metrics",
    "is_due",
    "shares_per_100",
]
