"""Constants for editorial workflow web-research enrichment (AE-0317)."""

# Hard bounds keeping the synchronous workflow-start latency budget predictable:
# at most 5 provided URLs are navigated, never more than 2 Chromium pages at a
# time, and at most 3 DuckDuckGo hits are appended as supplementary sources.
MAX_URL_SOURCES_SCRAPED = 5
MAX_CONCURRENT_SCRAPES = 2
MAX_WEB_SEARCH_RESULTS = 3

SOURCE_TYPE_WEB_SEARCH = "web_search"

# AE-0321: anti-bot/CDN block pages must not masquerade as research content
# (observed live: x.ai served a Cloudflare block page that became a "research
# finding"). Markers are matched case-insensitively against the head of the
# scraped text; a hit degrades gracefully to the original URL content.
BLOCK_PAGE_SCAN_CHARS = 600
BLOCK_PAGE_MARKERS = (
    "you have been blocked",
    "attention required! | cloudflare",
    "enable javascript and cookies to continue",
    "checking your browser before accessing",
    "verify you are human",
    "just a moment...",
)

__all__ = [
    "BLOCK_PAGE_MARKERS",
    "BLOCK_PAGE_SCAN_CHARS",
    "MAX_CONCURRENT_SCRAPES",
    "MAX_URL_SOURCES_SCRAPED",
    "MAX_WEB_SEARCH_RESULTS",
    "SOURCE_TYPE_WEB_SEARCH",
]
