"""X web-search collector (AE-0352).

Gherkin: tests/features/autopilot_signals.feature
  Scenario: X search keeps only recent status posts
  Scenario: Mirror resolver falls back on legal block
"""

from __future__ import annotations

from datetime import timedelta

import httpx
import pytest
import respx

from rag_backend.modules.autopilot.constants import (
    SOURCE_X_SEARCH,
    X_MAX_QUERIES_PER_RUN,
    X_SEARCH_MAX_RESULTS,
    X_SEARCH_QUERIES,
    X_SEARCH_TIMELIMIT,
)
from rag_backend.modules.autopilot.domain.ports import WebSearchHit, WebSearchQuery
from rag_backend.modules.autopilot.domain.x_status import XStatusTarget
from rag_backend.modules.autopilot.infrastructure.collectors.errors import UpstreamError
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import HttpxGetter
from rag_backend.modules.autopilot.infrastructure.collectors.x_resolver import (
    MirrorResolver,
    MirrorResolverConfig,
)
from rag_backend.modules.autopilot.infrastructure.collectors.x_web_search import (
    XWebSearchCollector,
    XWebSearchDependencies,
)
from tests.unit.autopilot.support import AS_OF, WINDOW, hours_before, snowflake_id

_SNIPPET = "agents are shipping"
_HTTP_TIMEOUT = 5.0


class _Search:
    def __init__(
        self, hits: list[WebSearchHit] | None = None, *, fail: bool = False
    ) -> None:
        self.hits = hits or []
        self.fail = fail
        self.queries: list[WebSearchQuery] = []

    async def search(self, query: WebSearchQuery) -> list[WebSearchHit]:
        self.queries.append(query)
        if self.fail:
            raise RuntimeError("ddgs down")
        return self.hits


class _Pause:
    def __init__(self) -> None:
        self.calls: list[float] = []

    async def pause(self, seconds: float) -> None:
        self.calls.append(seconds)


class _Jitter:
    def __init__(self, values: tuple[float, ...]) -> None:
        self._values = list(values)

    def seconds(self) -> float:
        return self._values.pop(0)


class _Resolver:
    def __init__(self, text: str | None) -> None:
        self.text = text
        self.calls = 0

    async def resolve(self, target: XStatusTarget) -> str | None:
        del target
        self.calls += 1
        return self.text


def _collector(
    search: _Search,
    *,
    resolver: _Resolver | MirrorResolver | None = None,
    queries: tuple[str, ...] = X_SEARCH_QUERIES,
    jitter: tuple[float, ...] = (2.5, 4.0, 3.0, 2.0, 5.0),
) -> tuple[XWebSearchCollector, _Pause]:
    pause = _Pause()
    chosen = resolver if resolver is not None else _Resolver(None)
    collector = XWebSearchCollector(
        XWebSearchDependencies(
            search=search,
            resolver=chosen,
            pause=pause,
            jitter=_Jitter(jitter),
            queries=queries,
        )
    )
    return collector, pause


def _hit(url: str, snippet: str = _SNIPPET) -> WebSearchHit:
    return WebSearchHit(url=url, title="Post", snippet=snippet)


# Scenario: X search keeps only recent status posts
@pytest.mark.asyncio
async def test_only_the_recent_status_is_kept() -> None:
    recent = snowflake_id(hours_before(2))
    old = snowflake_id(AS_OF - timedelta(days=3))
    hits = [
        _hit("https://x.com/someone"),
        _hit(f"https://x.com/old/status/{old}"),
        _hit(f"https://x.com/bob/status/{recent}"),
        _hit("https://x.com/search?q=agents"),
    ]
    collector, _pause = _collector(_Search(hits), queries=("q",))
    signals = await collector.collect(WINDOW)
    assert len(signals) == 1
    assert signals[0].url == f"https://x.com/bob/status/{recent}"
    assert signals[0].text == _SNIPPET
    assert signals[0].handle == "bob"
    assert signals[0].source.value == SOURCE_X_SEARCH
    assert signals[0].score_hint == 1


@pytest.mark.asyncio
async def test_twitter_host_is_canonicalised_and_boundary_age_is_kept() -> None:
    boundary = snowflake_id(AS_OF - timedelta(hours=48))
    just_old = snowflake_id(AS_OF - timedelta(hours=48, seconds=1))
    hits = [
        _hit(f"https://twitter.com/alice/status/{boundary}"),
        _hit(f"https://x.com/carol/status/{just_old}"),
    ]
    collector, _pause = _collector(_Search(hits), queries=("q",))
    signals = await collector.collect(WINDOW)
    assert [signal.url for signal in signals] == [
        f"https://x.com/alice/status/{boundary}"
    ]


@pytest.mark.asyncio
async def test_repeat_queries_raise_the_overlap_hint() -> None:
    recent = snowflake_id(hours_before(2))
    url = f"https://x.com/bob/status/{recent}"
    search = _Search([_hit(url)])
    collector, pause = _collector(search, jitter=(2.5, 4.0))
    signals = await collector.collect(WINDOW)
    assert signals[0].score_hint == len(X_SEARCH_QUERIES)
    assert [query.text for query in search.queries] == list(X_SEARCH_QUERIES)
    assert search.queries[0].timelimit == X_SEARCH_TIMELIMIT
    assert search.queries[0].max_results == X_SEARCH_MAX_RESULTS
    assert pause.calls == [2.5, 4.0]


@pytest.mark.asyncio
async def test_query_cap_is_six_and_a_total_search_failure_raises() -> None:
    queries = tuple(f"q{index}" for index in range(8))
    search = _Search(fail=True)
    collector, pause = _collector(search, queries=queries, jitter=(2.0,) * 7)
    with pytest.raises(UpstreamError):
        await collector.collect(WINDOW)
    assert len(search.queries) == X_MAX_QUERIES_PER_RUN
    assert len(pause.calls) == X_MAX_QUERIES_PER_RUN - 1


@pytest.mark.asyncio
async def test_none_resolver_does_not_touch_the_network() -> None:
    recent = snowflake_id(hours_before(2))
    search = _Search([_hit(f"https://x.com/bob/status/{recent}")])
    collector, _pause = _collector(search, resolver=_Resolver(None))
    with respx.mock(assert_all_called=False) as router:
        router.route().mock(side_effect=AssertionError("unexpected http"))
        signals = await collector.collect(WINDOW)
        assert router.calls.call_count == 0
    assert signals[0].text == _SNIPPET


# Scenario: Mirror resolver falls back on legal block
@pytest.mark.asyncio
async def test_mirror_451_keeps_the_snippet() -> None:
    recent = snowflake_id(hours_before(2))
    target_url = f"https://x.com/bob/status/{recent}"
    mirror = MirrorResolver(
        MirrorResolverConfig(http=HttpxGetter(_HTTP_TIMEOUT), host="mirror.example")
    )
    search = _Search([_hit(target_url)])
    collector, _pause = _collector(search, resolver=mirror, queries=("q",))
    with respx.mock(assert_all_called=True) as router:
        route = router.get(url__regex=r"https://mirror\.example/.*").mock(
            return_value=httpx.Response(451, text="unavailable for legal reasons")
        )
        signals = await collector.collect(WINDOW)
    assert signals[0].text == _SNIPPET
    requested = str(route.calls[0].request.url)
    assert requested == f"https://mirror.example/bob/status/{recent}"
    assert "x.com" not in requested
