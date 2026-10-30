"""Autopilot Instagram insights: metric sets, rates, baselines and the read.

Gherkin: tests/features/autopilot_ig_insights.feature
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest

from rag_backend.modules.autopilot.application.ig_insights_service import (
    IgInsightsDependencies,
    IgInsightsService,
)
from rag_backend.modules.autopilot.domain.ig_insights_query import (
    IgInsightsQueryError,
    resolve_query,
)
from rag_backend.modules.autopilot.domain.ig_media import (
    BaselineSample,
    IgInsightsRequest,
    IgMedia,
    MediaListCommand,
    MediaListResult,
    MediaProject,
    OpenBoost,
    ResolvedIgQuery,
    TimeWindow,
    age_hours,
    baselines,
    metrics_for,
    rates_for,
)
from rag_backend.modules.autopilot.domain.insights import (
    InsightMetrics,
    InsightSnapshot,
    PublishedPost,
    dashboard_metrics,
)
from rag_backend.modules.autopilot.ig_media_constants import (
    DEPRECATED_METRICS,
    ERR_SINCE_TOO_OLD,
    METRICS_FEED,
    METRICS_REELS,
    PRODUCT_FEED,
    PRODUCT_REELS,
)
from rag_backend.modules.autopilot.infrastructure.insights_models import (
    InstagramPostInsightsModel,
)
from rag_backend.modules.autopilot.infrastructure.insights_store import _write

_NOW = datetime(2026, 10, 29, 18, 0, tzinfo=UTC)
_MEDIA = "18034567890123456"


def test_metric_sets_skip_deprecated_names() -> None:
    # Scenario: Deprecated metrics are never requested
    assert DEPRECATED_METRICS.isdisjoint(METRICS_FEED)
    assert DEPRECATED_METRICS.isdisjoint(METRICS_REELS)
    assert "follows" in metrics_for(PRODUCT_FEED)
    assert "follows" not in metrics_for(PRODUCT_REELS)
    assert "ig_reels_avg_watch_time" in metrics_for(PRODUCT_REELS)
    assert "ig_reels_avg_watch_time" not in metrics_for(PRODUCT_FEED)
    assert "follows" not in metrics_for(None)


def test_rates_stay_null_without_a_divisor() -> None:
    # Scenario: Refused metric stays null
    empty = rates_for(InsightMetrics())
    assert empty.shares_per_100_views is None
    assert empty.engagement_rate is None
    full = rates_for(
        InsightMetrics(views=5400, reach=3900, saved=140, shares=96, follows=22, total_interactions=466)
    )
    assert full.shares_per_100_views == 1.78
    assert full.saves_per_100_reach == 3.59
    assert full.follows_per_1000_reach == 5.64
    assert full.engagement_rate == 0.1195


def test_baseline_median_ignores_null_rates() -> None:
    samples = (
        BaselineSample(product_type=PRODUCT_FEED, metrics=InsightMetrics(reach=100, views=200, shares=2)),
        BaselineSample(product_type=PRODUCT_FEED, metrics=InsightMetrics(reach=300)),
        BaselineSample(product_type=PRODUCT_REELS, metrics=InsightMetrics()),
    )
    found = baselines(samples)
    assert found[PRODUCT_FEED].sample_size == 2
    assert found[PRODUCT_FEED].median_reach == 200
    assert found[PRODUCT_REELS].sample_size == 1
    assert found[PRODUCT_REELS].median_reach is None


def test_since_older_than_90_days_is_rejected() -> None:
    request = IgInsightsRequest(
        since=_NOW - timedelta(days=91),
        until=None,
        limit=30,
        media_type=None,
        product_type=None,
        refresh=False,
    )
    with pytest.raises(IgInsightsQueryError) as caught:
        resolve_query(request, _NOW)
    assert caught.value.code == ERR_SINCE_TOO_OLD


def test_dashboard_write_does_not_clear_likes() -> None:
    # Scenario: Dashboard refresh does not clear likes
    row = InstagramPostInsightsModel(
        media_id=_MEDIA,
        fetched_at=_NOW,
        likes=12,
        comments=3,
    )
    snapshot = InsightSnapshot(
        media_id=_MEDIA,
        metrics=InsightMetrics(views=10, reach=8),
        fetched_at=_NOW,
        written=dashboard_metrics(),
    )
    _write(row, snapshot)
    assert row.likes == 12
    assert row.comments == 3
    assert row.views == 10


def test_age_hours() -> None:
    posted = _NOW - timedelta(hours=47, minutes=30)
    assert age_hours(posted, _NOW) == 47.5


class _Clock:
    def now(self) -> datetime:
        return _NOW


@dataclass
class _Media:
    fresh: bool = False
    rows: list[IgMedia] = field(default_factory=list)
    saved: list[IgMedia] = field(default_factory=list)
    commits: int = 0

    async def list_is_fresh(self, now: datetime) -> bool:
        del now
        return self.fresh

    async def upsert(self, items: Sequence[IgMedia], listed_at: datetime) -> None:
        del listed_at
        self.saved.extend(items)
        self.rows = list(items)

    async def in_window(self, window: TimeWindow) -> list[IgMedia]:
        return [row for row in self.rows if window.start <= row.posted_at < window.end]

    async def projects(self, media_ids: Sequence[str]) -> dict[str, MediaProject]:
        del media_ids
        return {}

    async def baseline_samples(self, window: TimeWindow) -> list[BaselineSample]:
        del window
        return []

    async def commit(self) -> None:
        self.commits += 1


@dataclass
class _Snaps:
    saved: list[InsightSnapshot] = field(default_factory=list)
    current: dict[str, InsightSnapshot] = field(default_factory=dict)

    async def published_posts(self, limit: int) -> list[PublishedPost]:
        del limit
        return []

    async def snapshots(self, media_ids: Sequence[str]) -> dict[str, InsightSnapshot]:
        return {media_id: self.current[media_id] for media_id in media_ids if media_id in self.current}

    async def save(self, snapshot: InsightSnapshot) -> None:
        self.saved.append(snapshot)
        self.current[snapshot.media_id] = snapshot

    async def commit(self) -> None:
        return None


@dataclass
class _List:
    result_items: tuple[IgMedia, ...] = ()
    truncated: bool = False
    calls: int = 0

    async def list_media(self, command: MediaListCommand) -> MediaListResult:
        del command
        self.calls += 1
        return MediaListResult(items=self.result_items, truncated=self.truncated)


@dataclass
class _Graph:
    calls: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)

    async def media_insights(self, media_id: str, metrics: tuple[str, ...] = ()) -> InsightMetrics:
        self.calls.append((media_id, metrics))
        if "ig_reels_avg_watch_time" in metrics:
            return InsightMetrics(views=10, reach=8, avg_watch_time_ms=1500)
        return InsightMetrics(views=10, reach=8, follows=1, likes=None)


def _post(media_id: str, product: str, hours: int) -> IgMedia:
    return IgMedia(
        media_id=media_id,
        media_type="CAROUSEL_ALBUM" if product == PRODUCT_FEED else "VIDEO",
        media_product_type=product,
        permalink=None,
        caption_excerpt=None,
        posted_at=_NOW - timedelta(hours=hours),
        like_count=None,
        comments_count=None,
    )


def _query() -> ResolvedIgQuery:
    return resolve_query(
        IgInsightsRequest(
            since=None,
            until=None,
            limit=30,
            media_type=None,
            product_type=None,
            refresh=False,
        ),
        _NOW,
    )


@pytest.mark.asyncio
async def test_unconfigured_reader_returns_empty() -> None:
    service = IgInsightsService(
        IgInsightsDependencies(media=_Media(), insights=_Snaps(), clock=_Clock())
    )
    report = await service.report(_query())
    assert report.configured is False
    assert report.items == ()


@pytest.mark.asyncio
async def test_feed_and_reel_metrics_differ() -> None:
    # Scenario: Account media with rates and baselines
    feed = _post("11111", PRODUCT_FEED, 10)
    reel = _post("22222", PRODUCT_REELS, 5)
    media = _Media()
    graphs = _Graph()
    listing = _List(result_items=(feed, reel))
    service = IgInsightsService(
        IgInsightsDependencies(
            media=media,
            insights=_Snaps(),
            clock=_Clock(),
            media_gateway=listing,
            insights_gateway=graphs,
        )
    )
    report = await service.report(_query())
    by_id = {item.media.media_id: item for item in report.items}
    assert by_id["11111"].metrics.follows == 1
    assert by_id["11111"].metrics.avg_watch_time_ms is None
    assert by_id["22222"].metrics.avg_watch_time_ms == 1500
    assert by_id["22222"].metrics.follows is None
    assert set(report.baseline) == {PRODUCT_FEED, PRODUCT_REELS}
    assert media.commits == 1


@pytest.mark.asyncio
async def test_fresh_list_skips_graph() -> None:
    media = _Media(fresh=True, rows=[_post("11111", PRODUCT_FEED, 2)])
    listing = _List()
    service = IgInsightsService(
        IgInsightsDependencies(
            media=media,
            insights=_Snaps(),
            clock=_Clock(),
            media_gateway=listing,
            insights_gateway=_Graph(),
        )
    )
    report = await service.report(_query())
    assert listing.calls == 0
    assert len(report.items) == 1


@dataclass
class _Boosts:
    async def open_for(self, media_ids: tuple[str, ...]) -> dict[str, OpenBoost]:
        return {
            media_id: OpenBoost(request_id="req-1", status="pending_approval")
            for media_id in media_ids
        }


@pytest.mark.asyncio
async def test_open_boost_is_attached_to_the_post() -> None:
    media = _Media(fresh=True, rows=[_post("11111", PRODUCT_FEED, 2)])
    service = IgInsightsService(
        IgInsightsDependencies(
            media=media,
            insights=_Snaps(),
            clock=_Clock(),
            media_gateway=_List(),
            insights_gateway=_Graph(),
            boosts=_Boosts(),
        )
    )
    report = await service.report(_query())
    assert report.items[0].boost is not None
    assert report.items[0].boost.status == "pending_approval"
