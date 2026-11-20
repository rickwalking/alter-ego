"""``GET /api/autopilot/reels``: query defaults, Graph fields and caches (ADR-0031)."""

from __future__ import annotations

SORT_VIEWS = "views_desc"
SORT_SHARES_RATE = "shares_rate_desc"
SORT_TIMESTAMP = "timestamp_desc"
SORTS: frozenset[str] = frozenset({SORT_VIEWS, SORT_SHARES_RATE, SORT_TIMESTAMP})

QUERY_MIN_AGE = "min_age_days"
QUERY_MAX_AGE = "max_age_days"
QUERY_LIMIT = "limit"
QUERY_CURSOR = "cursor"
QUERY_SORT = "sort"
QUERY_EXCLUDE = "exclude_reposted_days"
QUERY_PARAMS: frozenset[str] = frozenset({
    QUERY_MIN_AGE,
    QUERY_MAX_AGE,
    QUERY_LIMIT,
    QUERY_CURSOR,
    QUERY_SORT,
    QUERY_EXCLUDE,
})

DEFAULT_MIN_AGE_DAYS = 60
DEFAULT_MAX_AGE_DAYS = 730
DEFAULT_LIMIT = 50
MAX_LIMIT = 100
DEFAULT_EXCLUDE_DAYS = 90
MAX_AGE_DAYS_CAP = 3650
CURSOR_PREFIX = "o:"
CURSOR_MAX_OFFSET = 10_000

MSG_INTEGER = "must be a whole number"
MSG_RANGE = "out of range"
MSG_SORT = "one of views_desc, shares_rate_desc, timestamp_desc"
MSG_CURSOR = "not a cursor from next_cursor"
MSG_AGE_ORDER = "must not exceed max_age_days"
MSG_UNKNOWN_PARAM = "unknown query parameter"

REELS_FIELDS = (
    "id,media_type,media_product_type,permalink,shortcode,timestamp,caption,"
    "media_url,thumbnail_url"
)
MEDIA_FIELDS_ONE = (
    "id,media_type,media_product_type,permalink,shortcode,timestamp,caption,"
    "media_url,thumbnail_url,owner"
)
FIELD_SHORTCODE = "shortcode"
FIELD_MEDIA_URL = "media_url"
FIELD_THUMBNAIL_URL = "thumbnail_url"
FIELD_OWNER = "owner"
REELS_MAX_PAGES = 20
REELS_PAGE_SIZE = 50
REELS_PAGE_DEADLINE_SECONDS = 15.0
REELS_HTTP_TIMEOUT_SECONDS = 20.0
VIDEO_STREAM_TIMEOUT_SECONDS = 120.0
VIDEO_CHUNK_BYTES = 256 * 1024

INSIGHTS_REFRESH_PER_REQUEST = 30
FACTS_PROBE_PER_REQUEST = 15
GRAPH_CONCURRENCY = 5

CDN_EXPIRY_PARAM = "oe"
HEX_BASE = 16
MS_PER_SECOND = 1000
SECONDS_PER_DAY = 86_400
WATCH_RATIO_DIGITS = 4
USERNAME_MAX = 30
COLLABORATORS_JSON_MAX = 10

FFPROBE_BINARY = "ffprobe"
FFMPEG_BINARY = "ffmpeg"

LOG_REELS = "autopilot.reels"
LOG_LIST_FAILED = "list_failed"
LOG_PROBE_FAILED = "probe_failed"
LOG_COLLABORATORS_FAILED = "collaborators_failed"
LOG_INSIGHTS_FAILED = "insights_failed"

APP_STATE_REELS_GATEWAY = "autopilot_reels_gateway"
APP_STATE_REEL_PROBE = "autopilot_reel_probe"

__all__ = [name for name in dir() if name.isupper()]
