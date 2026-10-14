"""Stable error codes and Graph API literals for Instagram publish."""

from rag_backend.domain.constants.retry import (
    META_MAX_ATTEMPTS,
    META_POLL_INTERVAL_SECONDS,
    META_POLL_MAX_ATTEMPTS,
)

ERR_INSTAGRAM_API_REQUEST_FAILED = "instagram_api_request_failed"
ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED = "instagram_credentials_not_configured"
ERR_INSTAGRAM_IMAGE_COUNT_INVALID = "instagram_image_count_invalid"
ERR_INSTAGRAM_CONTAINER_FAILED = "instagram_container_failed"
ERR_INSTAGRAM_CONTAINER_TIMEOUT = "instagram_container_timeout"
ERR_INSTAGRAM_API_NO_ID = "instagram_api_no_id"
ERR_INSTAGRAM_QUOTA_UNREADABLE = "content_publishing_limit_unreadable"
# The container reports PUBLISHED but no recent carousel could be matched to
# it. Non-transient: retrying media_publish would double-post (QA r1 H2).
ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN = "instagram_published_media_unknown"

# Instagram Login (user tokens IGAA…) talks to graph.instagram.com.
# Page tokens can select graph.facebook.com via META_IG_GRAPH_BASE.
GRAPH_HOST_INSTAGRAM = "https://graph.instagram.com/v23.0"
GRAPH_HOST_FACEBOOK = "https://graph.facebook.com/v23.0"

MIN_INSTAGRAM_CAROUSEL_ITEMS = 2
MAX_INSTAGRAM_CAROUSEL_ITEMS = 10

HTTP_GET = "GET"
HTTP_POST = "POST"
GRAPH_PATH_MEDIA = "/{ig_user_id}/media"
GRAPH_PATH_MEDIA_PUBLISH = "/{ig_user_id}/media_publish"
GRAPH_PATH_PUBLISHING_LIMIT = "/{ig_user_id}/content_publishing_limit"
GRAPH_PATH_MEDIA_NODE = "/{media_id}"

FIELD_IMAGE_URL = "image_url"
FIELD_IS_CAROUSEL_ITEM = "is_carousel_item"
FIELD_MEDIA_TYPE = "media_type"
FIELD_CHILDREN = "children"
FIELD_CAPTION = "caption"
FIELD_CREATION_ID = "creation_id"
FIELD_STATUS_CODE = "status_code"
FIELD_PERMALINK = "permalink"
FIELD_ID = "id"
FIELD_FIELDS = "fields"
VALUE_TRUE = "true"
MEDIA_TYPE_CAROUSEL = "CAROUSEL"
CONTAINER_STATUS_FINISHED = "FINISHED"
CONTAINER_STATUS_IN_PROGRESS = "IN_PROGRESS"
CONTAINER_STATUS_ERROR = "ERROR"
CONTAINER_STATUS_EXPIRED = "EXPIRED"
CONTAINER_STATUS_PUBLISHED = "PUBLISHED"

# Recovering the media id of a container that was already published (H2).
FIELD_TIMESTAMP = "timestamp"
FIELD_LIMIT = "limit"
MEDIA_TYPE_CAROUSEL_ALBUM = "CAROUSEL_ALBUM"
RECENT_MEDIA_LIMIT = 5
# Media posted this long before our recorded container time still matches:
# our clock and Meta's can differ by a few seconds (QA r2 R3).
CONTAINER_CLOCK_SKEW_SECONDS = 60
GRAPH_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

# Worst-case wall time of one stepped publish (QA r2 R4a). Every Graph request
# has an overall deadline, and each is tried at most META_MAX_ATTEMPTS times.
# Requests: quota, an expired container's status, the item containers, the
# parent, the status polls, media_publish (or the media recovery), permalink.
GRAPH_REQUEST_DEADLINE_SECONDS = 30
GRAPH_REQUESTS_PER_PUBLISH = (
    1 + 1 + MAX_INSTAGRAM_CAROUSEL_ITEMS + 1 + META_POLL_MAX_ATTEMPTS + 1 + 1
)
GRAPH_PUBLISH_WORST_CASE_SECONDS = (
    GRAPH_REQUESTS_PER_PUBLISH * META_MAX_ATTEMPTS * GRAPH_REQUEST_DEADLINE_SECONDS
    + META_POLL_MAX_ATTEMPTS * META_POLL_INTERVAL_SECONDS
)

KEY_DATA = "data"
KEY_QUOTA_USAGE = "quota_usage"
KEY_CONFIG = "config"
KEY_QUOTA_TOTAL = "quota_total"
KEY_ERROR = "error"
KEY_CODE = "code"

PUBLISH_RESULT_PUBLISHED = "published"
PUBLISH_RESULT_FAILED = "failed"

# Meta rate-limit codes that arrive as HTTP 400 rather than 429.
TRANSIENT_META_ERROR_CODES = frozenset({"4", "17", "32", "613"})
TRANSIENT_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})

__all__ = [
    "CONTAINER_CLOCK_SKEW_SECONDS",
    "CONTAINER_STATUS_ERROR",
    "CONTAINER_STATUS_EXPIRED",
    "CONTAINER_STATUS_FINISHED",
    "CONTAINER_STATUS_IN_PROGRESS",
    "CONTAINER_STATUS_PUBLISHED",
    "ERR_INSTAGRAM_API_NO_ID",
    "ERR_INSTAGRAM_API_REQUEST_FAILED",
    "ERR_INSTAGRAM_CONTAINER_FAILED",
    "ERR_INSTAGRAM_CONTAINER_TIMEOUT",
    "ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED",
    "ERR_INSTAGRAM_IMAGE_COUNT_INVALID",
    "ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN",
    "ERR_INSTAGRAM_QUOTA_UNREADABLE",
    "FIELD_CAPTION",
    "FIELD_CHILDREN",
    "FIELD_CREATION_ID",
    "FIELD_FIELDS",
    "FIELD_ID",
    "FIELD_IMAGE_URL",
    "FIELD_IS_CAROUSEL_ITEM",
    "FIELD_LIMIT",
    "FIELD_MEDIA_TYPE",
    "FIELD_PERMALINK",
    "FIELD_STATUS_CODE",
    "FIELD_TIMESTAMP",
    "GRAPH_HOST_FACEBOOK",
    "GRAPH_HOST_INSTAGRAM",
    "GRAPH_PATH_MEDIA",
    "GRAPH_PATH_MEDIA_NODE",
    "GRAPH_PATH_MEDIA_PUBLISH",
    "GRAPH_PATH_PUBLISHING_LIMIT",
    "GRAPH_PUBLISH_WORST_CASE_SECONDS",
    "GRAPH_REQUESTS_PER_PUBLISH",
    "GRAPH_REQUEST_DEADLINE_SECONDS",
    "GRAPH_TIMESTAMP_FORMAT",
    "HTTP_GET",
    "HTTP_POST",
    "KEY_CODE",
    "KEY_CONFIG",
    "KEY_DATA",
    "KEY_ERROR",
    "KEY_QUOTA_TOTAL",
    "KEY_QUOTA_USAGE",
    "MAX_INSTAGRAM_CAROUSEL_ITEMS",
    "MEDIA_TYPE_CAROUSEL",
    "MEDIA_TYPE_CAROUSEL_ALBUM",
    "MIN_INSTAGRAM_CAROUSEL_ITEMS",
    "PUBLISH_RESULT_FAILED",
    "PUBLISH_RESULT_PUBLISHED",
    "RECENT_MEDIA_LIMIT",
    "TRANSIENT_HTTP_STATUS",
    "TRANSIENT_META_ERROR_CODES",
    "VALUE_TRUE",
]
