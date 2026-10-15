"""Instagram per-post insights constants (AE-0378, ADR-0021 D11).

The dashboard reads the latest stored snapshot per published post and asks
the Graph API again only when the snapshot is older than six hours. A metric
the Graph API does not return stays ``None`` ("n/d" in the UI), never 0.
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
# The newest published posts listed on the dashboard.
INSIGHTS_POST_LIMIT = 30
# Graph reads per dashboard request; the rest are refreshed on the next one.
INSIGHTS_REFRESH_PER_REQUEST = 10
SHARES_PER_VIEWS_BASE = 100

# Graph: ``GET /{media-id}/insights?metric=a,b,c``.
GRAPH_PATH_MEDIA_INSIGHTS = "/{media_id}/insights"
FIELD_METRIC = "metric"
FIELD_DATA = "data"
FIELD_NAME = "name"
FIELD_VALUES = "values"
FIELD_VALUE = "value"
FIELD_TOTAL_VALUE = "total_value"

# HTTP route (mounted under ``/api``).
INSIGHTS_ROUTER_PREFIX = "/instagram"
PATH_INSIGHTS = "/insights"
TAG_INSTAGRAM = "instagram"

# Tests install a fake gateway here (``app.state``).
APP_STATE_INSIGHTS_GATEWAY = "autopilot_insights_gateway"
INSIGHTS_HTTP_TIMEOUT_SECONDS = 15.0

LOG_INSIGHTS = "instagram.insights"
LOG_REFRESH_FAILED = "refresh_failed"
LOG_MEDIA_ID_INVALID = "media_id_invalid"

__all__ = [
    "APP_STATE_INSIGHTS_GATEWAY",
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
    "METRIC_FOLLOWS",
    "METRIC_PROFILE_VISITS",
    "METRIC_REACH",
    "METRIC_SAVED",
    "METRIC_SHARES",
    "METRIC_TOTAL_INTERACTIONS",
    "METRIC_VIEWS",
    "PATH_INSIGHTS",
    "SHARES_PER_VIEWS_BASE",
    "TABLE_POST_INSIGHTS",
    "TAG_INSTAGRAM",
]
