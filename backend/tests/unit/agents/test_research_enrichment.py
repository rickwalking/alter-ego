"""Unit tests for deterministic web-research enrichment (AE-0317).

Scenarios: tests/features/research_enrichment.feature
"""

from __future__ import annotations

import asyncio

from rag_backend.agents.research_enrichment import enrich_sources
from rag_backend.domain.constants.research_enrichment import (
    MAX_CONCURRENT_SCRAPES,
    MAX_URL_SOURCES_SCRAPED,
    MAX_WEB_SEARCH_RESULTS,
    SOURCE_TYPE_WEB_SEARCH,
)
from rag_backend.domain.models import ResearchSourceType
from rag_backend.domain.protocols import ResearchEnrichmentParams

_TOPIC = "ai frontier models"


class _StubResearchTool:
    """Deterministic ResearchTool double tracking calls and concurrency."""

    def __init__(
        self,
        page_text: str = "Scraped page text",
        hits: list[dict[str, str]] | None = None,
    ) -> None:
        self.page_text = page_text
        self.hits = hits if hits is not None else []
        self.scraped_urls: list[str] = []
        self.search_queries: list[str] = []
        self.active_scrapes = 0
        self.max_active_scrapes = 0

    async def scrape_url(self, url: str) -> str:
        self.active_scrapes += 1
        self.max_active_scrapes = max(self.max_active_scrapes, self.active_scrapes)
        await asyncio.sleep(0)
        self.scraped_urls.append(url)
        self.active_scrapes -= 1
        return self.page_text

    async def search_web(
        self, query: str, _source_types: list[ResearchSourceType]
    ) -> list[dict[str, str]]:
        self.search_queries.append(query)
        return self.hits


def _params(tool: _StubResearchTool | None) -> ResearchEnrichmentParams:
    return ResearchEnrichmentParams(topic=_TOPIC, research_tool=tool)


def _url_source(url: str) -> dict[str, str]:
    return {"title": "a url source", "content": url, "source_type": "url"}


class TestScraping:
    async def test_url_source_content_is_replaced_with_scraped_text(self) -> None:
        """Scenario: URL source is navigated and its content informs research."""
        tool = _StubResearchTool(page_text="Kimi K3 announcement body")
        sources = [_url_source("https://example.com/blog/kimi-k3")]

        enriched = await enrich_sources(sources, _params(tool))

        assert enriched[0]["content"] == "Kimi K3 announcement body"
        assert tool.scraped_urls == ["https://example.com/blog/kimi-k3"]

    async def test_original_sources_are_not_mutated(self) -> None:
        """Scenario: URL source is navigated (input list stays pristine)."""
        tool = _StubResearchTool()
        sources = [_url_source("https://example.com/a")]

        await enrich_sources(sources, _params(tool))

        assert sources[0]["content"] == "https://example.com/a"

    async def test_bare_url_note_source_is_navigated(self) -> None:
        """Scenario: Note source embedding a bare URL is also navigated."""
        tool = _StubResearchTool(page_text="page body")
        sources = [
            {"title": "note", "content": "https://example.com/x", "source_type": "note"}
        ]

        enriched = await enrich_sources(sources, _params(tool))

        assert enriched[0]["content"] == "page body"

    async def test_plain_text_source_is_not_scraped(self) -> None:
        tool = _StubResearchTool()
        sources = [{"title": "n", "content": "just some text", "source_type": "note"}]

        enriched = await enrich_sources(sources, _params(tool))

        assert enriched[0]["content"] == "just some text"
        assert tool.scraped_urls == []

    async def test_unsafe_url_is_blocked_and_content_preserved(self) -> None:
        """Scenario: Unsafe URL is blocked, workflow proceeds."""
        tool = _StubResearchTool()
        sources = [
            _url_source("http://169.254.169.254/latest/meta-data"),
            _url_source("file:///etc/passwd"),
            _url_source("http://localhost/admin"),
        ]

        enriched = await enrich_sources(sources, _params(tool))

        assert tool.scraped_urls == []
        assert enriched[0]["content"] == "http://169.254.169.254/latest/meta-data"
        assert enriched[1]["content"] == "file:///etc/passwd"
        assert enriched[2]["content"] == "http://localhost/admin"

    async def test_scrape_failure_keeps_original_content(self) -> None:
        """Scenario: Dead link degrades gracefully."""

        class _FailingTool(_StubResearchTool):
            async def scrape_url(self, url: str) -> str:
                raise TimeoutError("page timed out")

        tool = _FailingTool()
        sources = [_url_source("https://example.com/dead")]

        enriched = await enrich_sources(sources, _params(tool))

        assert enriched[0]["content"] == "https://example.com/dead"

    async def test_scrape_count_is_capped(self) -> None:
        """Scenario: Scrape volume is capped."""
        tool = _StubResearchTool()
        sources = [
            _url_source(f"https://example.com/{i}")
            for i in range(MAX_URL_SOURCES_SCRAPED + 2)
        ]

        enriched = await enrich_sources(sources, _params(tool))

        assert len(tool.scraped_urls) == MAX_URL_SOURCES_SCRAPED
        assert enriched[MAX_URL_SOURCES_SCRAPED]["content"].startswith("https://")

    async def test_scrape_concurrency_is_bounded(self) -> None:
        tool = _StubResearchTool()
        sources = [
            _url_source(f"https://example.com/{i}")
            for i in range(MAX_URL_SOURCES_SCRAPED)
        ]

        await enrich_sources(sources, _params(tool))

        assert tool.max_active_scrapes <= MAX_CONCURRENT_SCRAPES

    async def test_scraped_content_is_sanitized(self) -> None:
        tool = _StubResearchTool(page_text="<p>Hello <b>world</b></p>")
        sources = [_url_source("https://example.com/html")]

        enriched = await enrich_sources(sources, _params(tool))

        assert "<" not in enriched[0]["content"]
        assert "Hello" in enriched[0]["content"]


class TestTopicSearch:
    def _hits(self, count: int) -> list[dict[str, str]]:
        return [
            {
                "title": f"Hit {i}",
                "url": f"https://hit{i}.example.com",
                "snippet": f"Snippet {i}",
            }
            for i in range(count)
        ]

    async def test_search_hits_are_appended_as_web_search_sources(self) -> None:
        """Scenario: Topic is researched on DuckDuckGo."""
        tool = _StubResearchTool(hits=self._hits(2))

        enriched = await enrich_sources([], _params(tool))

        assert tool.search_queries == [_TOPIC]
        assert len(enriched) == 2
        assert enriched[0]["source_type"] == SOURCE_TYPE_WEB_SEARCH
        assert enriched[0]["title"] == "Hit 0"
        assert enriched[0]["content"] == "Snippet 0"
        assert enriched[0]["url"] == "https://hit0.example.com"

    async def test_search_hits_are_capped(self) -> None:
        """Scenario: Topic is researched on DuckDuckGo (cap half)."""
        tool = _StubResearchTool(hits=self._hits(MAX_WEB_SEARCH_RESULTS + 5))

        enriched = await enrich_sources([], _params(tool))

        assert len(enriched) == MAX_WEB_SEARCH_RESULTS

    async def test_hit_without_snippet_is_skipped(self) -> None:
        tool = _StubResearchTool(
            hits=[{"title": "t", "url": "https://x.example.com", "snippet": ""}]
        )

        enriched = await enrich_sources([], _params(tool))

        assert enriched == []

    async def test_search_failure_is_non_fatal(self) -> None:
        """Scenario: Search failure is non-fatal."""

        class _FailingSearch(_StubResearchTool):
            async def search_web(
                self, query: str, _source_types: list[ResearchSourceType]
            ) -> list[dict[str, str]]:
                raise RuntimeError("ddg unavailable")

        sources = [{"title": "n", "content": "text", "source_type": "note"}]

        enriched = await enrich_sources(sources, _params(_FailingSearch()))

        assert enriched == sources


class TestDisabled:
    async def test_none_research_tool_passes_sources_through(self) -> None:
        """Scenario: Enrichment disabled restores legacy behavior."""
        sources = [_url_source("https://example.com/a")]

        enriched = await enrich_sources(sources, _params(None))

        assert enriched is sources


class TestObservabilityEvents:
    """AE-0317 review r1 (M5): the spec-listed structlog events must fire."""

    async def test_blocked_url_logs_research_url_blocked(self) -> None:
        """Scenario: Unsafe URL is blocked, workflow proceeds (log half)."""
        from structlog.testing import capture_logs

        tool = _StubResearchTool()
        with capture_logs() as logs:
            await enrich_sources(
                [_url_source("http://169.254.169.254/latest/meta-data")],
                _params(tool),
            )
        blocked = [log for log in logs if log["event"] == "research_url_blocked"]
        assert len(blocked) == 1
        assert blocked[0]["url"] == "http://169.254.169.254/latest/meta-data"
        assert blocked[0]["log_level"] == "warning"

    async def test_cap_overflow_logs_research_url_cap_hit(self) -> None:
        """Scenario: Scrape volume is capped (log half)."""
        from structlog.testing import capture_logs

        tool = _StubResearchTool()
        sources = [
            _url_source(f"https://example.com/{i}")
            for i in range(MAX_URL_SOURCES_SCRAPED + 2)
        ]
        with capture_logs() as logs:
            await enrich_sources(sources, _params(tool))
        cap_hits = [log for log in logs if log["event"] == "research_url_cap_hit"]
        assert len(cap_hits) == 2

    async def test_search_failure_logs_research_search_failed(self) -> None:
        """Scenario: Search failure is non-fatal (log half)."""
        from structlog.testing import capture_logs

        class _FailingSearch(_StubResearchTool):
            async def search_web(
                self, query: str, _source_types: list[ResearchSourceType]
            ) -> list[dict[str, str]]:
                raise RuntimeError("ddg unavailable")

        with capture_logs() as logs:
            await enrich_sources([], _params(_FailingSearch()))
        failed = [log for log in logs if log["event"] == "research_search_failed"]
        assert len(failed) == 1
        assert failed[0]["topic"] == _TOPIC


class TestCapSemantics:
    """AE-0317 review r1 (m7): unsafe URLs must not consume scrape budget."""

    async def test_unsafe_urls_do_not_consume_scrape_budget(self) -> None:
        tool = _StubResearchTool()
        unsafe = [
            _url_source("http://localhost/a"),
            _url_source("http://127.0.0.1/b"),
        ]
        safe = [
            _url_source(f"https://example.com/{i}")
            for i in range(MAX_URL_SOURCES_SCRAPED)
        ]

        await enrich_sources(unsafe + safe, _params(tool))

        assert len(tool.scraped_urls) == MAX_URL_SOURCES_SCRAPED
        assert all(url.startswith("https://example.com/") for url in tool.scraped_urls)


class TestConcurrencyBound:
    """AE-0317 review r1 (m10): deterministic semaphore-width assertion."""

    async def test_semaphore_admits_exactly_the_configured_width(self) -> None:
        class _GatedTool(_StubResearchTool):
            """Blocks every scrape until the full semaphore width is in flight."""

            def __init__(self) -> None:
                super().__init__()
                self.gate = asyncio.Event()

            async def scrape_url(self, url: str) -> str:
                self.active_scrapes += 1
                self.max_active_scrapes = max(
                    self.max_active_scrapes, self.active_scrapes
                )
                if self.active_scrapes >= MAX_CONCURRENT_SCRAPES:
                    self.gate.set()
                # If the semaphore admitted fewer than MAX_CONCURRENT_SCRAPES
                # tasks, this wait times out, the scrape degrades gracefully,
                # and the assertion below fails.
                await asyncio.wait_for(self.gate.wait(), timeout=1)
                self.scraped_urls.append(url)
                self.active_scrapes -= 1
                return self.page_text

        tool = _GatedTool()
        sources = [
            _url_source(f"https://example.com/{i}")
            for i in range(MAX_URL_SOURCES_SCRAPED)
        ]

        await enrich_sources(sources, _params(tool))

        assert tool.max_active_scrapes == MAX_CONCURRENT_SCRAPES
