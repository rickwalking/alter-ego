"""Assertion-bearing tests that pin exact research enrichment helpers.

Feature: Research enrichment of carousel sources
"""

from unittest.mock import AsyncMock

import pytest
from structlog.testing import capture_logs

from rag_backend.agents.research_enrichment import (
    _is_scrapeable,
    _relevant_source,
    _search_topic_sources,
)
from rag_backend.domain.constants.carousel_workflow import SOURCE_TYPE_URL

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
