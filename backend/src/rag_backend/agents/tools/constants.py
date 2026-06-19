"""Constants for the agents-package research tool adapters (AE-0249)."""

from __future__ import annotations

from rag_backend.domain.models import ResearchSourceType

# Tool names exposed to the researcher subagent.
TOOL_SCRAPE_URL = "scrape_url"
TOOL_SEARCH_WEB = "search_web"

# Graceful-degradation message returned when a URL cannot be reached, so the
# researcher continues without the page instead of failing the whole run
# (ADR-0249 "scrape failure degrades gracefully" scenario).
SCRAPE_FAILURE_PREFIX = "scrape failed for"

# search_web result formatting.
EMPTY_SEARCH_RESULT = "No web results found."
SEARCH_RESULT_TEMPLATE = "[{index}] {title} ({url})\n{snippet}"
SOURCE_KEY_URL = "url"
SOURCE_KEY_TITLE = "title"
SOURCE_KEY_SNIPPET = "snippet"

# Default source types the researcher searches across when none are supplied.
DEFAULT_SEARCH_SOURCE_TYPES: tuple[ResearchSourceType, ...] = (
    ResearchSourceType.BLOG,
    ResearchSourceType.NEWS,
    ResearchSourceType.DOCUMENTATION,
)

__all__ = [
    "DEFAULT_SEARCH_SOURCE_TYPES",
    "EMPTY_SEARCH_RESULT",
    "SCRAPE_FAILURE_PREFIX",
    "SEARCH_RESULT_TEMPLATE",
    "SOURCE_KEY_SNIPPET",
    "SOURCE_KEY_TITLE",
    "SOURCE_KEY_URL",
    "TOOL_SCRAPE_URL",
    "TOOL_SEARCH_WEB",
]
