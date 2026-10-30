"""Instagram per-post insights constants (ADR-0021 D11).

The dashboard reads the latest stored snapshot per published post and asks
the Graph API again only when the snapshot is older than six hours. A metric
the Graph API does not return stays ``None`` ("n/d" in the UI), never 0.

Graph is read for a bounded number of posts per dashboard request; the rest are
refreshed on the next one. Tests install a fake gateway on ``app.state``.
"""

from __future__ import annotations

TABLE_POST_INSIGHTS = "instagram_post_insights"

METRIC_VIEWS = "views"
METRIC_REACH = "reach"
METRIC_SAVED = "saved"
METRIC_SHARES = "shares"
METRIC_FOLLOWS = "follows"
METRIC_PROFILE_VISITS = "profile_visits"
METRIC_TOTAL_INTERACTIONS = "total_interactions"
METRIC_LIKES = "likes"
METRIC_COMMENTS = "comments"
METRIC_AVG_WATCH_TIME = "ig_reels_avg_watch_time"
METRIC_TOTAL_WATCH_TIME = "ig_reels_video_view_total_time"
COLUMN_AVG_WATCH_TIME = "avg_watch_time_ms"
COLUMN_TOTAL_WATCH_TIME = "total_watch_time_ms"
INSIGHT_METRICS: tuple[str, ...] = (
    METRIC_VIEWS,
    METRIC_REACH,
    METRIC_SAVED,
    METRIC_SHARES,
    METRIC_FOLLOWS,
    METRIC_PROFILE_VISITS,
    METRIC_TOTAL_INTERACTIONS,
)

INSIGHTS_TTL_HOURS = 6
INSIGHTS_POST_LIMIT = 30
INSIGHTS_REFRESH_PER_REQUEST = 10
SHARES_PER_VIEWS_BASE = 100

GRAPH_PATH_MEDIA_INSIGHTS = "/{media_id}/insights"
FIELD_METRIC = "metric"
FIELD_DATA = "data"
FIELD_NAME = "name"
FIELD_VALUES = "values"
FIELD_VALUE = "value"
FIELD_TOTAL_VALUE = "total_value"

INSIGHTS_ROUTER_PREFIX = "/instagram"
PATH_INSIGHTS = "/insights"
TAG_INSTAGRAM = "instagram"
CHANNEL_INSTAGRAM = "instagram"

APP_STATE_INSIGHTS_GATEWAY = "autopilot_insights_gateway"
INSIGHTS_HTTP_TIMEOUT_SECONDS = 15.0

LOG_INSIGHTS = "instagram.insights"
LOG_REFRESH_FAILED = "refresh_failed"
LOG_MEDIA_ID_INVALID = "media_id_invalid"

__all__ = [
    "APP_STATE_INSIGHTS_GATEWAY",
    "CHANNEL_INSTAGRAM",
    "COLUMN_AVG_WATCH_TIME",
    "COLUMN_TOTAL_WATCH_TIME",
    "FIELD_DATA",
    "FIELD_METRIC",
    "FIELD_NAME",
    "FIELD_TOTAL_VALUE",
    "FIELD_VALUE",
    "FIELD_VALUES",
    "GRAPH_PATH_MEDIA_INSIGHTS",
    "INSIGHTS_HTTP_TIMEOUT_SECONDS",
    "INSIGHTS_POST_LIMIT",
    "INSIGHTS_REFRESH_PER_REQUEST",
    "INSIGHTS_ROUTER_PREFIX",
    "INSIGHTS_TTL_HOURS",
    "INSIGHT_METRICS",
    "LOG_INSIGHTS",
    "LOG_MEDIA_ID_INVALID",
    "LOG_REFRESH_FAILED",
    "METRIC_AVG_WATCH_TIME",
    "METRIC_COMMENTS",
    "METRIC_FOLLOWS",
    "METRIC_LIKES",
    "METRIC_PROFILE_VISITS",
    "METRIC_REACH",
    "METRIC_SAVED",
    "METRIC_SHARES",
    "METRIC_TOTAL_INTERACTIONS",
    "METRIC_TOTAL_WATCH_TIME",
    "METRIC_VIEWS",
    "PATH_INSIGHTS",
    "SHARES_PER_VIEWS_BASE",
    "TABLE_POST_INSIGHTS",
    "TAG_INSTAGRAM",
]
