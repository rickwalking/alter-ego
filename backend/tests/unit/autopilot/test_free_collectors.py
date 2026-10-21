"""Hacker News, Hugging Face, Bluesky, and GitHub collectors.

Gherkin: tests/features/autopilot_signals.feature
  Scenario: Bundle combines all free sources
Network calls are mocked with respx.
"""

from __future__ import annotations

import json
from datetime import timedelta

import httpx
import pytest
import respx

from rag_backend.modules.autopilot.constants import (
    BSKY_ORIGIN,
    BSKY_TRENDS_URL,
    GITHUB_SEARCH_URL,
    HEADER_USER_AGENT,
    HF_DAILY_PAPERS_URL,
    HN_MIN_POINTS,
    HN_SEARCH_QUERIES,
    HN_SEARCH_URL,
    HTTP_USER_AGENT,
    SOURCE_BLUESKY,
    SOURCE_GITHUB,
    SOURCE_HF_PAPERS,
    SOURCE_HN,
)
from rag_backend.modules.autopilot.infrastructure.collectors.bluesky import (
    BlueskyTrendsCollector,
)
from rag_backend.modules.autopilot.infrastructure.collectors.errors import UpstreamError
from rag_backend.modules.autopilot.infrastructure.collectors.github_search import (
    GitHubSearchCollector,
    GitHubSearchConfig,
)
from rag_backend.modules.autopilot.infrastructure.collectors.hacker_news import (
    HackerNewsCollector,
    signals_from_hn,
)
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import HttpxGetter
from rag_backend.modules.autopilot.infrastructure.collectors.huggingface_papers import (
    HuggingFacePapersCollector,
)
from tests.unit.autopilot.support import AS_OF, WINDOW

_HTTP = HttpxGetter(5.0)


def _hn_hit(
    *,
    points: int = 150,
    created_at: str = "2026-10-13T14:00:00Z",
    url: str | None = "https://example.com/post",
    object_id: str = "42",
    title: str = "Claude update",
) -> dict[str, object]:
    hit: dict[str, object] = {
        "title": title,
        "points": points,
        "objectID": object_id,
        "created_at": created_at,
        "author": "alice",
        "story_text": "",
    }
    if url is not None:
        hit["url"] = url
    return hit


def test_hn_parser_drops_low_points_stale_hits_and_fills_item_urls() -> None:
    stale = (AS_OF - timedelta(hours=49)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "hits": [
            _hn_hit(),
            _hn_hit(points=HN_MIN_POINTS, object_id="low"),
            _hn_hit(created_at=stale, object_id="old"),
            _hn_hit(url=None, object_id="99", title="Ask HN"),
            {"title": "broken"},
        ]
    }
    signals = signals_from_hn(payload, WINDOW)
    assert [signal.url for signal in signals] == [
        "https://example.com/post",
        "https://news.ycombinator.com/item?id=99",
    ]
    assert signals[0].source.value == SOURCE_HN
    assert signals[0].score_hint == 150
    assert signals[0].handle == "alice"
    assert signals_from_hn(["nope"], WINDOW) == []


@pytest.mark.asyncio
async def test_hn_requests_algolia_with_the_documented_filters() -> None:
    body = json.dumps({"hits": [_hn_hit()]})
    with respx.mock(assert_all_called=True) as router:
        route = router.get(HN_SEARCH_URL).mock(
            return_value=httpx.Response(200, text=body)
        )
        signals = await HackerNewsCollector(_HTTP).collect(WINDOW)
    assert len(signals) == len(HN_SEARCH_QUERIES)
    requested = route.calls[0].request
    filters = requested.url.params["numericFilters"]
    assert "points>100" in filters
    assert "created_at_i>" in filters
    assert requested.url.params["tags"] == "story"
    assert requested.url.params["query"] == HN_SEARCH_QUERIES[0]
    assert requested.headers[HEADER_USER_AGENT] == HTTP_USER_AGENT


@pytest.mark.asyncio
async def test_hn_non_json_and_http_errors_raise() -> None:
    with respx.mock(assert_all_called=True) as router:
        router.get(HN_SEARCH_URL).mock(
            return_value=httpx.Response(200, text="not-json")
        )
        with pytest.raises(UpstreamError):
            await HackerNewsCollector(_HTTP).collect(WINDOW)
    with respx.mock(assert_all_called=True) as router:
        router.get(HN_SEARCH_URL).mock(return_value=httpx.Response(503, text="down"))
        with pytest.raises(UpstreamError):
            await HackerNewsCollector(_HTTP).collect(WINDOW)


@pytest.mark.asyncio
async def test_huggingface_daily_papers_are_mapped() -> None:
    payload = [
        {
            "title": "Paper",
            "summary": "A summary",
            "publishedAt": "2026-10-13T00:00:00.000Z",
            "paper": {
                "id": "2609.36642",
                "title": "Paper",
                "summary": "A summary",
                "upvotes": 12,
            },
        },
        {"paper": {"title": "missing id"}},
        "nope",
    ]
    with respx.mock(assert_all_called=True) as router:
        route = router.get(HF_DAILY_PAPERS_URL).mock(
            return_value=httpx.Response(200, text=json.dumps(payload))
        )
        signals = await HuggingFacePapersCollector(_HTTP).collect(WINDOW)
        assert route.call_count == 1
    assert len(signals) == 1
    assert signals[0].source.value == SOURCE_HF_PAPERS
    assert signals[0].url == "https://huggingface.co/papers/2609.36642"
    assert signals[0].score_hint == 12
    assert signals[0].text == "A summary"


@pytest.mark.asyncio
async def test_bluesky_relative_links_become_absolute() -> None:
    payload = {
        "trends": [
            {
                "topic": "abc",
                "displayName": "New model",
                "link": "/profile/did:plc:abc/feed/abc",
                "startedAt": "2026-10-13T12:00:00+00:00",
                "postCount": 40,
                "description": "People are posting about it",
            },
            {
                "displayName": "Absolute",
                "link": "https://bsky.app/search?q=agents",
                "startedAt": "2026-10-13T12:00:00+00:00",
            },
            {"displayName": "No link", "startedAt": "2026-10-13T12:00:00+00:00"},
        ]
    }
    with respx.mock(assert_all_called=True) as router:
        route = router.get(BSKY_TRENDS_URL).mock(
            return_value=httpx.Response(200, text=json.dumps(payload))
        )
        signals = await BlueskyTrendsCollector(_HTTP).collect(WINDOW)
        assert route.calls[0].request.url.params["limit"] == "10"
    assert signals[0].url == f"{BSKY_ORIGIN}/profile/did:plc:abc/feed/abc"
    assert signals[0].source.value == SOURCE_BLUESKY
    assert signals[0].text == "People are posting about it"
    assert signals[0].score_hint == 40
    assert signals[1].url == "https://bsky.app/search?q=agents"
    assert len(signals) == 2


def _github(token: str) -> GitHubSearchCollector:
    return GitHubSearchCollector(GitHubSearchConfig(http=_HTTP, token=token))


@pytest.mark.asyncio
async def test_github_sends_the_token_only_when_configured() -> None:
    payload = {
        "items": [
            {
                "full_name": "org/llm",
                "html_url": "https://github.com/org/llm",
                "description": "An LLM repo",
                "stargazers_count": 20,
                "created_at": "2026-10-10T00:00:00Z",
                "owner": {"login": "org"},
            },
            {"full_name": "skip/me"},
        ]
    }
    body = json.dumps(payload)
    with respx.mock(assert_all_called=True) as router:
        route = router.get(GITHUB_SEARCH_URL).mock(
            return_value=httpx.Response(200, text=body)
        )
        signals = await _github("sekret").collect(WINDOW)
    request = route.calls[0].request
    assert request.headers["authorization"] == "Bearer sekret"
    assert "topic:llm" in request.url.params["q"]
    assert "created:>" in request.url.params["q"]
    assert request.url.params["sort"] == "stars"
    assert signals[0].source.value == SOURCE_GITHUB
    assert signals[0].handle == "org"
    assert signals[0].score_hint == 20
    with respx.mock(assert_all_called=True) as router:
        route = router.get(GITHUB_SEARCH_URL).mock(
            return_value=httpx.Response(200, text=body)
        )
        await _github("  ").collect(WINDOW)
    assert "authorization" not in route.calls[0].request.headers
