"""The Reels list: query, cursor, rates, sort, baseline and the service.

Gherkin: tests/features/autopilot_reels_list_ae0626.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta

import pytest

from rag_backend.modules.autopilot.application.reels_service import (
    REEL_METRICS,
    ReelsDeps,
    ReelsService,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.insights import (
    InsightMetrics,
    InsightSnapshot,
)
from rag_backend.modules.autopilot.domain.reels import (
    ReelFacts,
    ReelItem,
    baseline,
    cdn_expiry,
    reel_rates,
    sort_items,
    watch_ratio,
)
from rag_backend.modules.autopilot.domain.reels_query import (
    ReelsQuery,
    decode_cursor,
    encode_cursor,
    parse_reels_query,
)
from rag_backend.modules.autopilot.domain.repost import RepostError
from rag_backend.modules.autopilot.repost_constants import (
    STATUS_PENDING,
    STATUS_PUBLISHED,
)
from tests.unit.modules.autopilot.repost_fakes import (
    NOW,
    Clock,
    FakeProbe,
    FakeReels,
    MemoryStore,
    reel,
    stored,
)


# Scenario: A bad query parameter is refused
@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"limit": "500"}, "limit"),
        ({"limit": "0"}, "limit"),
        ({"limit": "x"}, "limit"),
        ({"min_age_days": "-1"}, "min_age_days"),
        ({"min_age_days": "100", "max_age_days": "50"}, "min_age_days"),
        ({"sort": "likes"}, "sort"),
        ({"cursor": "%%%"}, "cursor"),
        ({"cursor": encode_cursor(99_999)}, "cursor"),
        ({"exclude_reposted_days": "9999"}, "exclude_reposted_days"),
        ({"foo": "1"}, "foo"),
    ],
)
def test_bad_query(params: dict[str, str], field: str) -> None:
    with pytest.raises(RepostError) as error:
        parse_reels_query(params)
    assert error.value.problem.status == 400
    assert error.value.problem.field == field


def test_query_defaults_and_values() -> None:
    assert parse_reels_query({}) == ReelsQuery()
    query = parse_reels_query({
        "limit": "2",
        "sort": "timestamp_desc",
        "cursor": encode_cursor(4),
        "min_age_days": "0",
        "max_age_days": "10",
        "exclude_reposted_days": "0",
    })
    assert (
        query.limit,
        query.sort,
        query.offset,
        query.min_age_days,
        query.max_age_days,
        query.exclude_reposted_days,
    ) == (2, "timestamp_desc", 4, 0, 10, 0)


def test_cursor_round_trip_and_garbage() -> None:
    assert decode_cursor(encode_cursor(42)) == 42
    assert decode_cursor(None) == 0
    assert decode_cursor("") == 0
    import base64

    for raw in (b"x:1", b"o:abc", b"\xff\xfe"):
        cursor = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        with pytest.raises(RepostError):
            decode_cursor(cursor)


# Scenario: Rates, watch ratio and baseline
def test_rates_and_watch_ratio() -> None:
    rates = reel_rates(
        InsightMetrics(views=1000, shares=50, reach=800, avg_watch_time_ms=4500), 9.0
    )
    assert rates.base.shares_per_100_views == 5.0
    assert rates.avg_watch_ratio == 0.5
    assert watch_ratio(None, 9.0) is None
    assert watch_ratio(1000, None) is None
    assert watch_ratio(1000, 0.0) is None


def test_cdn_expiry() -> None:
    assert cdn_expiry("https://cdn/v.mp4?oe=6740ABCD") == datetime.fromtimestamp(
        0x6740ABCD, tz=UTC
    )
    assert cdn_expiry(None) is None
    assert cdn_expiry("https://cdn/v.mp4") is None
    assert cdn_expiry("https://cdn/v.mp4?oe=zz") is None
    assert cdn_expiry("https://cdn/v.mp4?oe=FFFFFFFFFFFFFFFF") is None


def _item(
    media_id: str, views: int | None, shares: int | None = None, days: int = 100
) -> ReelItem:
    metrics = InsightMetrics(
        views=views,
        shares=shares,
        reach=views,
        total_interactions=None if views is None else views // 10,
    )
    return ReelItem(
        media=reel(media_id, days_old=days),
        facts=None,
        metrics=metrics,
        rates=reel_rates(metrics, None),
        stale=False,
        age_days=days,
        last_repost=None,
    )


# Scenario: Reels are sorted by views by default
# Scenario: Sorting by shares rate and by timestamp
def test_sort_orders() -> None:
    items = [
        _item("1", 500, 50, days=100),
        _item("2", 9000, 9, days=200),
        _item("3", None, days=90),
    ]
    assert [i.media.media_id for i in sort_items(items, "views_desc")] == [
        "2",
        "1",
        "3",
    ]
    assert [i.media.media_id for i in sort_items(items, "shares_rate_desc")] == [
        "1",
        "2",
        "3",
    ]
    assert [i.media.media_id for i in sort_items(items, "timestamp_desc")] == [
        "3",
        "1",
        "2",
    ]


def test_baseline_medians() -> None:
    result = baseline([_item("1", 100, 10), _item("2", 300, 3), _item("3", None)])
    assert result.median_views == 200.0
    assert result.median_shares_per_100_views == 5.5
    assert result.median_engagement_rate == 0.1
    empty = baseline([])
    assert (
        empty.median_views,
        empty.median_shares_per_100_views,
        empty.median_engagement_rate,
    ) == (None, None, None)


@dataclass
class _Insights:
    rows: dict[str, InsightSnapshot] = field(default_factory=dict)
    saved: list[InsightSnapshot] = field(default_factory=list)

    async def published_posts(self, limit: int) -> list[object]:
        del limit
        return []

    async def snapshots(self, media_ids: object) -> dict[str, InsightSnapshot]:
        return {m: self.rows[m] for m in media_ids if m in self.rows}

    async def save(self, snapshot: InsightSnapshot) -> None:
        self.saved.append(snapshot)
        self.rows[snapshot.media_id] = snapshot

    async def commit(self) -> None:
        return None


@dataclass
class _InsightsGateway:
    views: dict[str, int] = field(default_factory=dict)
    fail: bool = False
    calls: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)

    async def media_insights(
        self, media_id: str, metrics: tuple[str, ...] = ()
    ) -> InsightMetrics:
        self.calls.append((media_id, metrics))
        if self.fail:
            raise InstagramCallError(status_code=500, error_code="x", transient=True)
        return InsightMetrics(views=self.views.get(media_id, 0), shares=1, reach=100)


@dataclass
class _World:
    reels: FakeReels
    insights: _Insights
    gateway: _InsightsGateway
    store: MemoryStore
    probe: FakeProbe

    def service(self, *, graph: bool = True) -> ReelsService:
        return ReelsService(
            ReelsDeps(
                reels=self.reels if graph else None,
                insights_gateway=self.gateway if graph else None,
                insights=self.insights,
                facts=self.store,
                reposts=self.store,
                probe=self.probe,
                clock=Clock(),
            )
        )


def _world(*reels_: object) -> _World:
    items = {r.media_id: r for r in reels_}
    return _World(
        reels=FakeReels(items=items, collaborator_names={"2": ("rick",)}),
        insights=_Insights(),
        gateway=_InsightsGateway(views={"1": 500, "2": 9000, "3": 50}),
        store=MemoryStore(),
        probe=FakeProbe(seconds=10.0),
    )


# Scenario: Only Reels inside the age window are listed
async def test_age_window() -> None:
    world = _world(reel("1", 30), reel("2", 90), reel("3", 800))
    page = await world.service().page(ReelsQuery())
    assert [i.media.media_id for i in page.items] == ["2"]
    assert page.generated_at == NOW


# Scenario: Reels are sorted by views by default
# Scenario: Paging with an opaque cursor
async def test_sort_and_paging() -> None:
    world = _world(reel("1", 100), reel("2", 200), reel("3", 300))
    service = world.service()
    first = await service.page(ReelsQuery(limit=2))
    assert [i.media.media_id for i in first.items] == ["2", "1"]
    assert first.next_cursor is not None
    second = await service.page(
        ReelsQuery(limit=2, offset=decode_cursor(first.next_cursor))
    )
    assert [i.media.media_id for i in second.items] == ["3"]
    assert second.next_cursor is None
    assert first.baseline.median_views == 500.0


# Scenario: Durations and collaborators are probed once and cached
async def test_facts_and_insights_are_cached() -> None:
    world = _world(reel("2", 200))
    service = world.service()
    page = await service.page(ReelsQuery())
    item = page.items[0]
    assert item.facts is not None and item.facts.collaborators == ("rick",)
    assert item.rates.avg_watch_ratio is None
    assert not item.stale
    assert world.gateway.calls[0][1] == REEL_METRICS
    await service.page(ReelsQuery())
    assert world.probe.calls == 1
    assert len(world.gateway.calls) == 1


# Scenario: A stale snapshot is refreshed, a failed refresh is marked stale
async def test_stale_snapshot_refresh_and_failure() -> None:
    world = _world(reel("1", 100))
    old = InsightSnapshot(
        media_id="1",
        metrics=InsightMetrics(views=7),
        fetched_at=NOW - timedelta(hours=7),
    )
    world.insights.rows["1"] = old
    page = await world.service().page(ReelsQuery())
    assert page.items[0].metrics.views == 500 and not page.items[0].stale
    world2 = _world(reel("1", 100))
    world2.insights.rows["1"] = old
    world2.gateway.fail = True
    page = await world2.service().page(ReelsQuery())
    assert page.items[0].metrics.views == 7 and page.items[0].stale


async def test_collaborator_failure_skips_facts() -> None:
    world = _world(reel("1", 100))

    class _Bad(FakeReels):
        async def collaborators(self, media_id: str) -> tuple[str, ...]:
            raise InstagramCallError(status_code=500, error_code="x", transient=True)

    world.reels = _Bad(items=world.reels.items)
    page = await world.service().page(ReelsQuery())
    assert page.items[0].facts is None
    world2 = _world(replace(reel("1", 100), video_url=None))
    page = await world2.service().page(ReelsQuery())
    assert page.items[0].facts is not None and page.items[0].facts.duration_s is None


# Scenario: Reposted Reels are hidden
async def test_reposted_reels_hidden_unless_window_is_zero() -> None:
    world = _world(reel("1", 100), reel("9", 70))
    pending = stored(
        media_id="1", created_at=NOW - timedelta(days=10), status=STATUS_PENDING
    )
    published = stored(
        media_id="5",
        status=STATUS_PUBLISHED,
        new_media_id="9",
        created_at=NOW - timedelta(days=200),
    )
    world.store.rows[pending.id] = pending
    world.store.rows[published.id] = published
    service = world.service()
    assert (await service.page(ReelsQuery())).items == ()
    page = await service.page(ReelsQuery(exclude_reposted_days=0))
    assert [i.media.media_id for i in page.items] == ["1"]
    last = page.items[0].last_repost
    assert last is not None and last.repost_id == pending.id


# Scenario: Instagram is not configured
async def test_unconfigured_and_graph_failure() -> None:
    world = _world(reel("1", 100))
    with pytest.raises(RepostError) as error:
        await world.service(graph=False).page(ReelsQuery())
    assert (error.value.problem.code, error.value.problem.status) == (
        "instagram_not_configured",
        503,
    )
    world.reels.fail = InstagramCallError(
        status_code=500, error_code="x", transient=True
    )
    with pytest.raises(RepostError) as error:
        await world.service().page(ReelsQuery())
    assert error.value.problem.code == "instagram_unavailable"


async def test_no_insights_gateway_keeps_snapshots() -> None:
    world = _world(reel("1", 100))
    service = ReelsService(
        ReelsDeps(
            reels=world.reels,
            insights_gateway=None,
            insights=world.insights,
            facts=world.store,
            reposts=world.store,
            probe=None,
            clock=Clock(),
        )
    )
    page = await service.page(ReelsQuery())
    assert page.items[0].stale and page.items[0].metrics.views is None
    facts = page.items[0].facts
    assert isinstance(facts, ReelFacts) and facts.duration_s is None
