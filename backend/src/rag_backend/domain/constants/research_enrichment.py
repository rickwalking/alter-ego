"""Constants for editorial workflow web-research enrichment (AE-0317)."""

# Hard bounds keeping the synchronous workflow-start latency budget predictable:
# at most 5 provided URLs are navigated, never more than 2 Chromium pages at a
# time, and at most 3 DuckDuckGo hits are appended as supplementary sources.
MAX_URL_SOURCES_SCRAPED = 5
MAX_CONCURRENT_SCRAPES = 2
MAX_WEB_SEARCH_RESULTS = 3

SOURCE_TYPE_WEB_SEARCH = "web_search"

__all__ = [
    "MAX_CONCURRENT_SCRAPES",
    "MAX_URL_SOURCES_SCRAPED",
    "MAX_WEB_SEARCH_RESULTS",
    "SOURCE_TYPE_WEB_SEARCH",
]
