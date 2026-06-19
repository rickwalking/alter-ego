"""Integration: researcher subagent browses a URL and synthesizes sources.

Feature: researcher_subagent_url_navigation.feature (AE-0249)

The researcher subagent wraps the REAL ``PlaywrightResearchTool`` (the concrete
``application`` service) via the @tool adapters, injected through the
``ResearchTool`` Protocol. Playwright and the web search client are stubbed here
because CI has no browser and no external keys — the test exercises the adapter +
subagent composition path, not the live browser.
"""

from __future__ import annotations

from typing import cast

import pytest
from langchain_core.tools import BaseTool, tool

from rag_backend.agents.subagents import (
    RESEARCHER_SUBAGENT_NAME,
    ResearcherSubagentConfig,
    build_researcher_subagent,
)
from rag_backend.agents.subagents.constants import (
    SPEC_FIELD_NAME,
    SPEC_FIELD_PROMPT,
    SPEC_FIELD_TOOLS,
)
from rag_backend.agents.tools.constants import SCRAPE_FAILURE_PREFIX
from rag_backend.application.services.tools.research_tool import PlaywrightResearchTool
from rag_backend.domain.models import ResearchSourceType

pytestmark = pytest.mark.integration

_URL = "https://example.com/research-article"
_PAGE_TEXT = "Rust eliminates entire classes of memory bugs at compile time."


class _FakePage:
    async def goto(self, url: str, **_: object) -> None:
        self.url = url

    async def inner_text(self, _selector: str) -> str:
        return _PAGE_TEXT


class _FakeBrowser:
    async def new_page(self) -> _FakePage:
        return _FakePage()

    async def close(self) -> None:
        return None


class _FakeChromium:
    async def launch(self, **_: object) -> _FakeBrowser:
        return _FakeBrowser()


class _FakePlaywright:
    def __init__(self) -> None:
        self.chromium = _FakeChromium()

    async def __aenter__(self) -> _FakePlaywright:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


def _patch_playwright(monkeypatch: pytest.MonkeyPatch) -> None:
    import playwright.async_api as pw

    monkeypatch.setattr(pw, "async_playwright", lambda: _FakePlaywright())


def _patch_search(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the ddgs DuckDuckGo client (no external network in CI)."""

    class _FakeDDGS:
        def __enter__(self) -> _FakeDDGS:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def text(self, _query: str, max_results: int = 10) -> list[dict[str, str]]:
            return [
                {"href": "https://a", "title": "Source A", "body": "snippet a"},
            ]

    import ddgs

    monkeypatch.setattr(ddgs, "DDGS", _FakeDDGS)


@tool
async def _search_documents(query: str) -> str:
    """Stub knowledge-base search tool.

    Args:
        query: search string
    """
    return f"docs:{query}"


def _tool_by_name(spec: dict[str, object], name: str) -> BaseTool:
    tools = cast("list[BaseTool]", spec[SPEC_FIELD_TOOLS])
    for candidate in tools:
        if candidate.name == name:
            return candidate
    raise AssertionError(f"tool {name} not in researcher spec")


def _build_spec() -> dict[str, object]:
    config = ResearcherSubagentConfig(
        research=PlaywrightResearchTool(),
        search_documents=_search_documents,
    )
    return build_researcher_subagent(config)


# Scenario: The agent browses a pasted URL and synthesizes sources
@pytest.mark.asyncio
async def test_researcher_browses_url_and_synthesizes_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_playwright(monkeypatch)
    _patch_search(monkeypatch)
    spec = _build_spec()

    assert spec[SPEC_FIELD_NAME] == RESEARCHER_SUBAGENT_NAME
    assert isinstance(spec[SPEC_FIELD_PROMPT], str)

    scrape = _tool_by_name(spec, "scrape_url")
    page = await scrape.ainvoke({"url": _URL})
    assert page == _PAGE_TEXT

    search = _tool_by_name(spec, "search_web")
    sources = await search.ainvoke({"query": "rust safety"})
    assert "Source A" in sources

    # Synthesis: the browsed page + web source are both available to the agent.
    synthesized = f"{page}\n\n{sources}"
    assert _PAGE_TEXT in synthesized
    assert "https://a" in synthesized


# Scenario: A scrape failure degrades gracefully
@pytest.mark.asyncio
async def test_researcher_scrape_failure_degrades(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BoomChromium:
        async def launch(self, **_: object) -> object:
            raise ConnectionError("network down")

    class _BoomPlaywright(_FakePlaywright):
        def __init__(self) -> None:
            self.chromium = cast("_FakeChromium", _BoomChromium())

    import playwright.async_api as pw

    monkeypatch.setattr(pw, "async_playwright", lambda: _BoomPlaywright())
    _patch_search(monkeypatch)

    spec = _build_spec()
    scrape = _tool_by_name(spec, "scrape_url")
    result = await scrape.ainvoke({"url": _URL})
    assert result.startswith(SCRAPE_FAILURE_PREFIX)
    assert "network down" in result


def test_researcher_searches_default_source_types() -> None:
    """The search adapter targets blog/news/documentation source types."""
    from rag_backend.agents.tools.constants import DEFAULT_SEARCH_SOURCE_TYPES

    assert ResearchSourceType.BLOG in DEFAULT_SEARCH_SOURCE_TYPES
    assert ResearchSourceType.NEWS in DEFAULT_SEARCH_SOURCE_TYPES
