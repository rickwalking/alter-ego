"""Instagram insights: KPI rules, the refresh service and the Graph reader.

Gherkin: tests/features/instagram_insights.feature
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from rag_backend.infrastructure.external.meta_instagram_publisher import (
    MetaInstagramPublisherConfig,
)
from rag_backend.modules.autopilot.application.insights_service import (
    InsightsDependencies,
    InstagramInsightsService,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.insights import (
    InsightMetrics,
    InsightSnapshot,
    PostInsightsRow,
    PublishedPost,
    build_report,
    is_due,
    shares_per_100,
)
from rag_backend.modules.autopilot.infrastructure.insights_gateway import (
    GraphInsightsGateway,
    parse_insights,
)

_NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
_FULL = InsightMetrics(
    views=1000, reach=800, saved=40, shares=10, follows=3, profile_visits=25
)


@pytest.mark.unit
class TestRules:
    def test_due_after_six_hours(self) -> None:
        snap = InsightSnapshot(media_id="1", metrics=_FULL, fetched_at=_NOW)
        assert is_due(None, _NOW)
        assert not is_due(snap, _NOW + timedelta(hours=5, minutes=59))
        assert is_due(snap, _NOW + timedelta(hours=6))

    def test_shares_per_100(self) -> None:
        assert shares_per_100(10, 1000) == 1.0
        assert shares_per_100(1, 3) == 33.33
        assert shares_per_100(None, 1000) is None
        assert shares_per_100(5, None) is None
        assert shares_per_100(5, 0) is None

    # Scenario: Ratios use only posts that report the metric
    def test_report_ratios(self) -> None:
        rows = [
            _row("1", _FULL),
            _row("2", InsightMetrics(views=1000, shares=None)),
            _row("3", InsightMetrics()),
        ]
        report = build_report(rows)
        assert report.follows_total == 3
        assert report.follows_per_post == 3.0
        assert report.shares_per_100_views == 1.0
        assert rows[0].shares_per_100_views == 1.0
        empty = build_report([])
        assert empty.follows_per_post is None
        assert empty.shares_per_100_views is None


def _row(media_id: str, metrics: InsightMetrics) -> PostInsightsRow:
    return PostInsightsRow(
        post=PublishedPost(media_id=media_id),
        metrics=metrics,
        fetched_at=_NOW,
        stale=False,
    )


class _Clock:
    def now(self) -> datetime:
        return _NOW


@dataclass
class _Store:
    posts: list[PublishedPost]
    stored: dict[str, InsightSnapshot] = field(default_factory=dict)
    commits: int = 0

    async def published_posts(self, limit: int) -> list[PublishedPost]:
        return self.posts[:limit]

    async def snapshots(self, media_ids: Sequence[str]) -> dict[str, InsightSnapshot]:
        return {m: self.stored[m] for m in media_ids if m in self.stored}

    async def save(self, snapshot: InsightSnapshot) -> None:
        self.stored[snapshot.media_id] = snapshot

    async def commit(self) -> None:
        self.commits += 1


@dataclass
class _Gateway:
    metrics: dict[str, InsightMetrics] = field(default_factory=dict)
    fail: bool = False
    calls: list[str] = field(default_factory=list)

    async def media_insights(self, media_id: str) -> InsightMetrics:
        self.calls.append(media_id)
        if self.fail:
            raise InstagramCallError(status_code=500, error_code="x", transient=True)
        return self.metrics.get(media_id, InsightMetrics())


def _service(store: _Store, gateway: _Gateway | None) -> InstagramInsightsService:
    return InstagramInsightsService(
        InsightsDependencies(store=store, clock=_Clock(), gateway=gateway)
    )


def _posts(*ids: str) -> list[PublishedPost]:
    return [PublishedPost(media_id=i, topic=f"Post {i}") for i in ids]


@pytest.mark.unit
class TestService:
    # Scenario: Fresh insights for published posts
    @pytest.mark.asyncio
    async def test_fresh_rows_are_read_and_stored(self) -> None:
        store = _Store(posts=_posts("1", "2"))
        gateway = _Gateway(metrics={"1": _FULL, "2": InsightMetrics(views=5)})
        report = await _service(store, gateway).report()
        assert [r.metrics for r in report.rows] == [_FULL, InsightMetrics(views=5)]
        assert all(not r.stale and r.fetched_at == _NOW for r in report.rows)
        assert set(store.stored) == {"1", "2"}
        assert store.commits == 1

    # Scenario: A recent snapshot is served without calling Graph
    @pytest.mark.asyncio
    async def test_recent_snapshot_skips_graph(self) -> None:
        old = _NOW - timedelta(hours=2)
        store = _Store(posts=_posts("1"))
        store.stored["1"] = InsightSnapshot(media_id="1", metrics=_FULL, fetched_at=old)
        gateway = _Gateway()
        report = await _service(store, gateway).report()
        assert gateway.calls == []
        assert report.rows[0].metrics == _FULL
        assert not report.rows[0].stale
        assert store.commits == 0

    # Scenario: Graph failure keeps the last snapshot
    @pytest.mark.asyncio
    async def test_failure_keeps_the_stale_snapshot(self) -> None:
        old = _NOW - timedelta(hours=7)
        store = _Store(posts=_posts("1", "2"))
        store.stored["1"] = InsightSnapshot(media_id="1", metrics=_FULL, fetched_at=old)
        report = await _service(store, _Gateway(fail=True)).report()
        first, second = report.rows
        assert first.metrics == _FULL
        assert first.stale
        assert first.fetched_at == old
        assert second.metrics == InsightMetrics()
        assert second.stale
        assert store.commits == 0

    # Scenario: No Instagram account configured
    @pytest.mark.asyncio
    async def test_unconfigured_serves_snapshots_as_stale(self) -> None:
        store = _Store(posts=_posts("1"))
        report = await _service(store, None).report()
        assert report.rows[0].stale
        assert report.rows[0].metrics == InsightMetrics()

    @pytest.mark.asyncio
    async def test_refresh_budget_per_request(self) -> None:
        ids = [str(i) for i in range(1, 15)]
        store = _Store(posts=_posts(*ids))
        gateway = _Gateway()
        report = await _service(store, gateway).report()
        assert len(gateway.calls) == 10
        assert [r.stale for r in report.rows].count(True) == 4


def _payload(**values: int) -> dict[str, object]:
    return {
        "data": [
            {"name": name, "period": "lifetime", "values": [{"value": value}]}
            for name, value in values.items()
        ]
    }


@dataclass
class _Token:
    value: str

    async def get(self) -> str:
        return self.value


def _gateway(
    handler: httpx.MockTransport, *, with_token: bool = True
) -> tuple[GraphInsightsGateway, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=handler)
    config = MetaInstagramPublisherConfig(
        ig_user_id="17841400000000000",
        graph_base="https://graph.instagram.com/v22.0",
        token_provider=_Token("tok" if with_token else ""),
    )
    return GraphInsightsGateway(config, client), client


@pytest.mark.unit
class TestGraphReader:
    def test_parse_both_shapes(self) -> None:
        body = _payload(views=100, reach=80)
        data = body["data"]
        assert isinstance(data, list)
        data.append({"name": "follows", "total_value": {"value": 2}})
        data.append({"name": "saved", "values": [{"value": True}]})
        data.append("junk")
        assert parse_insights(body) == {"views": 100, "reach": 80, "follows": 2}
        assert parse_insights({"data": "x"}) == {}

    # Scenario: Missing metric
    @pytest.mark.asyncio
    async def test_one_call_and_missing_metric(self) -> None:
        seen: list[httpx.Request] = []

        def handle(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json=_payload(views=100, shares=4))

        gateway, client = _gateway(httpx.MockTransport(handle))
        async with client:
            metrics = await gateway.media_insights("1789")
        assert metrics == InsightMetrics(views=100, shares=4)
        assert metrics.follows is None
        assert len(seen) == 1
        assert seen[0].url.path == "/v22.0/1789/insights"
        assert "follows" in seen[0].url.params["metric"]

    # Scenario: Graph refuses the metric list
    @pytest.mark.asyncio
    async def test_refused_list_reads_each_metric(self) -> None:
        def handle(request: httpx.Request) -> httpx.Response:
            metric = request.url.params["metric"]
            if "," in metric or metric == "follows":
                return httpx.Response(400, json={"error": {"code": 100}})
            return httpx.Response(200, json=_payload(**{metric: 7}))

        gateway, client = _gateway(httpx.MockTransport(handle))
        async with client:
            metrics = await gateway.media_insights("1789")
        assert metrics.views == 7
        assert metrics.total_interactions == 7
        assert metrics.follows is None

    @pytest.mark.asyncio
    async def test_transient_failure_raises(self) -> None:
        gateway, client = _gateway(
            httpx.MockTransport(lambda _request: httpx.Response(503))
        )
        async with client:
            with pytest.raises(InstagramCallError) as caught:
                await gateway.media_insights("1789")
        assert caught.value.transient

    @pytest.mark.asyncio
    async def test_missing_token_raises_and_odd_ids_are_empty(self) -> None:
        calls: list[httpx.Request] = []

        def handle(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(200, json=_payload(views=1))

        gateway, client = _gateway(httpx.MockTransport(handle), with_token=False)
        async with client:
            with pytest.raises(InstagramCallError):
                await gateway.media_insights("1789")
            assert await gateway.media_insights("../me") == InsightMetrics()
        assert calls == []
