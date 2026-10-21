"""Constants for editorial workflow web-research enrichment.

Hard bounds keep the synchronous workflow-start latency predictable: at most 5
provided URLs are navigated, never more than 2 Chromium pages at a time, and at
most 3 DuckDuckGo hits are appended as supplementary sources.

Anti-bot/CDN block pages must not masquerade as research content (a Cloudflare
block page once became a "research finding"). The markers are matched
case-insensitively against the head of the scraped text; a hit degrades to the
original URL content.

Web-search hits must be Portuguese or English and on topic (a bracketed QA tag
once pulled Russian pages into the outline). Bracketed tags are dropped from the
search query; a hit needs mostly Latin letters, a PT or EN stopword when long
enough to judge, and a keyword stem shared with the query.
"""

MAX_URL_SOURCES_SCRAPED = 5
MAX_CONCURRENT_SCRAPES = 2
MAX_WEB_SEARCH_RESULTS = 3

SOURCE_TYPE_WEB_SEARCH = "web_search"

BLOCK_PAGE_SCAN_CHARS = 600
BLOCK_PAGE_MARKERS = (
    "you have been blocked",
    "attention required! | cloudflare",
    "enable javascript and cookies to continue",
    "checking your browser before accessing",
    "verify you are human",
    "just a moment...",
)

MIN_LATIN_LETTER_RATIO = 0.8
MIN_LANGUAGE_FILTER_WORDS = 8
MIN_KEYWORD_CHARS = 4
KEYWORD_STEM_CHARS = 5
LOG_RESEARCH_HIT_FILTERED = "research_hit_filtered"
FILTER_REASON_LANGUAGE = "language"
FILTER_REASON_OFF_TOPIC = "off_topic"

__all__ = [
    "BLOCK_PAGE_MARKERS",
    "BLOCK_PAGE_SCAN_CHARS",
    "FILTER_REASON_LANGUAGE",
    "FILTER_REASON_OFF_TOPIC",
    "KEYWORD_STEM_CHARS",
    "LOG_RESEARCH_HIT_FILTERED",
    "MAX_CONCURRENT_SCRAPES",
    "MAX_URL_SOURCES_SCRAPED",
    "MAX_WEB_SEARCH_RESULTS",
    "MIN_KEYWORD_CHARS",
    "MIN_LANGUAGE_FILTER_WORDS",
    "MIN_LATIN_LETTER_RATIO",
    "SOURCE_TYPE_WEB_SEARCH",
]
