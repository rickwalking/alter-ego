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

# SSRF boundary guard (AE-0249 QA F-1): the researcher subagent is LLM-driven, so
# the scrape_url argument is untrusted. Only http(s) is allowed, and host-internal
# targets (loopback/private/link-local incl. the cloud metadata endpoint) are
# refused before the Playwright service is invoked.
SCRAPE_BLOCKED_PREFIX = "scrape blocked for"
ALLOWED_URL_SCHEMES = ("http", "https")
BLOCKED_URL_HOSTNAMES = ("localhost", "metadata.google.internal")

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
    "ALLOWED_URL_SCHEMES",
    "BLOCKED_URL_HOSTNAMES",
    "DEFAULT_SEARCH_SOURCE_TYPES",
    "EMPTY_SEARCH_RESULT",
    "SCRAPE_BLOCKED_PREFIX",
    "SCRAPE_FAILURE_PREFIX",
    "SEARCH_RESULT_TEMPLATE",
    "SOURCE_KEY_SNIPPET",
    "SOURCE_KEY_TITLE",
    "SOURCE_KEY_URL",
    "TOOL_SCRAPE_URL",
    "TOOL_SEARCH_WEB",
]
