"""Constants for the agents-package research tool adapters.

SCRAPE_FAILURE_PREFIX marks the graceful-degradation message returned when a URL cannot
be reached, so the researcher continues without the page instead of failing the whole
run.

SCRAPE_BLOCKED_PREFIX marks the SSRF boundary guard: the researcher is LLM-driven, so
the scrape_url argument is untrusted. Only http(s) is allowed, and host-internal targets
(loopback, private, link-local including the cloud metadata endpoint) are refused before
the Playwright service is invoked. The scheme and host lists live in the domain so the
application scraper shares them.
"""

from __future__ import annotations

from rag_backend.domain.constants.url_safety import (
    ALLOWED_URL_SCHEMES,
    BLOCKED_URL_HOSTNAMES,
)
from rag_backend.domain.models import ResearchSourceType

TOOL_SCRAPE_URL = "scrape_url"
TOOL_SEARCH_WEB = "search_web"

SCRAPE_FAILURE_PREFIX = "scrape failed for"

SCRAPE_BLOCKED_PREFIX = "scrape blocked for"

EMPTY_SEARCH_RESULT = "No web results found."
SEARCH_RESULT_TEMPLATE = "[{index}] {title} ({url})\n{snippet}"
SOURCE_KEY_URL = "url"
SOURCE_KEY_TITLE = "title"
SOURCE_KEY_SNIPPET = "snippet"

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
