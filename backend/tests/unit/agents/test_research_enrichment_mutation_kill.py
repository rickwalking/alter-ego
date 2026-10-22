"""Assertion-bearing tests that pin exact research enrichment helpers.

Feature: Research enrichment of carousel sources
"""

from unittest.mock import AsyncMock, patch

import pytest
from structlog.testing import capture_logs

from rag_backend.agents.research_enrichment import (
    _is_scrapeable,
    _relevant_source,
    _search_topic_sources,
    _select_scrape_jobs,
)
from rag_backend.agents.tools.constants import DEFAULT_SEARCH_SOURCE_TYPES
from rag_backend.domain.constants.carousel_workflow import SOURCE_TYPE_URL
from rag_backend.domain.constants.research_enrichment import (
    LOG_RESEARCH_HIT_FILTERED,
    MAX_URL_SOURCES_SCRAPED,
)

SEARCH_FAILED_EVENT = "research_search_failed"


# Scenario: Sources without usable content are never scraped
@pytest.mark.parametrize(
    "source",
    [
        {"source_type": SOURCE_TYPE_URL},
        {"content": "", "source_type": SOURCE_TYPE_URL},
    ],
)
def test_source_without_content_is_not_scrapeable(source: dict[str, str]) -> None:
    """A URL-typed source with missing or empty content is skipped."""
    assert _is_scrapeable(source) is False


# Scenario: A URL-typed source is scraped even when not a bare URL
def test_url_typed_source_is_scrapeable() -> None:
    """The url source type alone makes a source scrapeable."""
    source = {"content": "see the article", "source_type": SOURCE_TYPE_URL}

    assert _is_scrapeable(source) is True


# Scenario: A non-URL source with plain text is not scraped
def test_plain_text_document_is_not_scrapeable() -> None:
    """A document source with plain text is not scrapeable."""
    source = {"content": "plain notes here", "source_type": "document"}

    assert _is_scrapeable(source) is False


# Scenario: A failing web search is logged with its error
async def test_search_failure_logs_error_text() -> None:
    """The search failure log carries the exception message."""
    tool = AsyncMock()
    tool.search_web = AsyncMock(side_effect=RuntimeError("search exploded"))

    with capture_logs() as logs:
        result = await _search_topic_sources(tool, "kubernetes")

    assert result == []
    failures = [log for log in logs if log["event"] == SEARCH_FAILED_EVENT]
    assert len(failures) == 1
    assert failures[0]["error"] == "search exploded"
    assert failures[0]["topic"] == "kubernetes"


# Scenario: A hit whose title alone matches the query is kept
def test_hit_matching_only_by_title_is_kept() -> None:
    """The title takes part in the relevance check."""
    hit = {
        "title": "Kubernetes guide",
        "snippet": "This article explains how the cluster scheduler works today",
        "url": "https://example.com/a",
    }

    source = _relevant_source(hit, "kubernetes")

    assert source is not None
    assert source["title"] == "Kubernetes guide"
    assert source["url"] == "https://example.com/a"


# Scenario: A URL over the scrape cap is logged with its address
async def test_cap_hit_log_carries_skipped_url() -> None:
    """The cap-hit warning names the URL that was skipped."""
    urls = [f"https://example.com/{i}" for i in range(MAX_URL_SOURCES_SCRAPED + 1)]
    sources = [{"content": url, "source_type": SOURCE_TYPE_URL} for url in urls]

    with (
        patch(
            "rag_backend.agents.research_enrichment.is_safe_research_target",
            new=AsyncMock(return_value=True),
        ),
        capture_logs() as logs,
    ):
        jobs = await _select_scrape_jobs(sources)

    assert jobs == list(range(MAX_URL_SOURCES_SCRAPED))
    capped = [log for log in logs if log["event"] == "research_url_cap_hit"]
    assert len(capped) == 1
    assert capped[0]["url"] == urls[-1]


# Scenario: The topic search asks for the default source types
async def test_search_requests_default_source_types() -> None:
    """The search tool receives the default source type list."""
    tool = AsyncMock()
    tool.search_web = AsyncMock(return_value=[])

    await _search_topic_sources(tool, "kubernetes")

    assert tool.search_web.await_args.args[1] == list(DEFAULT_SEARCH_SOURCE_TYPES)


# Scenario: A hit without a url keeps an empty url
def test_hit_without_url_has_empty_url() -> None:
    """A kept hit lacking a url yields an empty url, not a placeholder."""
    hit = {
        "title": "Kubernetes guide",
        "snippet": "This article explains how the cluster scheduler works today",
    }

    source = _relevant_source(hit, "kubernetes")

    assert source is not None
    assert source["url"] == ""


# Scenario: A filtered hit is logged with its url and reason
def test_filtered_hit_log_carries_event_url_and_reason() -> None:
    """The filter log has the event name, the hit url and a rejection reason."""
    hit = {
        "title": "Weather",
        "snippet": "The weather today is sunny and the cat is on the mat",
        "url": "https://example.com/weather",
    }

    with capture_logs() as logs:
        source = _relevant_source(hit, "kubernetes")

    assert source is None
    assert len(logs) == 1
    assert logs[0]["event"] == LOG_RESEARCH_HIT_FILTERED
    assert logs[0]["url"] == "https://example.com/weather"
    assert logs[0]["reason"]
