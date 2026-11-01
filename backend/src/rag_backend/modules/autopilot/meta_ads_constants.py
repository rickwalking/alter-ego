"""Marketing API (Graph v23.0) names for the boost launch: calls, targeting, errors.

Targeting for an ``ON_POST`` engagement boost of an existing Instagram post:

- ``geo_locations.countries`` and ``age_min``/``age_max`` come from the stored request
  audience and must sit inside the shipped caps (Brazil only, ages 18-65).
- ``publisher_platforms=["instagram"]`` with ``instagram_positions=["stream"]`` keeps
  delivery on the Instagram feed, where the boosted post lives.
- ``targeting_automation.advantage_audience=0`` stops Meta from widening the audience
  past the caps (v23 requires the flag to be set explicitly on new ad sets).

The ad set runs from ``start_time`` to ``end_time`` (unix seconds), ``days`` long and
never more than the 7-day cap, so Meta stops spending on its own side too.
"""

from __future__ import annotations

CALL_PREFLIGHT_MEDIA = "preflight_media"
CALL_PREFLIGHT_ACCOUNT = "preflight_account"
CALL_MIN_BUDGETS = "min_budgets"
CALL_CAMPAIGN = "campaign"
CALL_ADSET = "adset"
CALL_CREATIVE = "creative"
CALL_AD = "ad"
CALL_ACTIVATE = "activate"
CALL_PAUSE = "pause"

FIELD_CALL = "call"
FIELD_CODE = "code"
FIELD_SUBCODE = "error_subcode"
FIELD_TYPE = "type"
FIELD_MESSAGE = "message"
FIELD_USER_TITLE = "error_user_title"
FIELD_USER_MSG = "error_user_msg"
FIELD_TRACE = "fbtrace_id"
FIELD_HTTP_STATUS = "http_status"
META_ERROR_FIELDS = (
    FIELD_CODE,
    FIELD_SUBCODE,
    FIELD_TYPE,
    FIELD_MESSAGE,
    FIELD_USER_TITLE,
    FIELD_USER_MSG,
    FIELD_TRACE,
)
DETAIL_MAX_CHARS = 500
REDACTED = "[redacted]"

ERR_PREFIX_META = "meta_"
ERR_META_TRANSIENT = "meta_transient"
ERR_META_BAD_BODY = "meta_bad_body"
ERR_META_NO_ID = "meta_no_id"
ERR_APP_DEV_MODE = "meta_app_dev_mode"
ERR_MEDIA_UNREADABLE = "meta_media_unreadable"
ERR_SCHEDULE = "boost_schedule_invalid"

META_CODE_PARAM = 100
META_SUBCODE_UNSUPPORTED_GET = 33
META_SUBCODE_APP_DEV_MODE = 1885183

TARGET_GEO = "geo_locations"
TARGET_COUNTRIES = "countries"
TARGET_AGE_MIN = "age_min"
TARGET_AGE_MAX = "age_max"
TARGET_PLATFORMS = "publisher_platforms"
TARGET_IG_POSITIONS = "instagram_positions"
TARGET_AUTOMATION = "targeting_automation"
TARGET_ADVANTAGE = "advantage_audience"
PLATFORM_INSTAGRAM = "instagram"
IG_POSITION_FEED = "stream"
ADVANTAGE_OFF = 0
ALLOWED_AD_COUNTRIES: frozenset[str] = frozenset({"BR"})

EXECUTION_OPTIONS = "execution_options"
VALIDATE_ONLY = "validate_only"
VALIDATE_ONLY_VALUE = '["validate_only"]'

__all__ = [
    "ADVANTAGE_OFF",
    "ALLOWED_AD_COUNTRIES",
    "CALL_ACTIVATE",
    "CALL_AD",
    "CALL_ADSET",
    "CALL_CAMPAIGN",
    "CALL_CREATIVE",
    "CALL_MIN_BUDGETS",
    "CALL_PAUSE",
    "CALL_PREFLIGHT_ACCOUNT",
    "CALL_PREFLIGHT_MEDIA",
    "DETAIL_MAX_CHARS",
    "ERR_APP_DEV_MODE",
    "ERR_MEDIA_UNREADABLE",
    "ERR_META_BAD_BODY",
    "ERR_META_NO_ID",
    "ERR_META_TRANSIENT",
    "ERR_PREFIX_META",
    "ERR_SCHEDULE",
    "EXECUTION_OPTIONS",
    "FIELD_CALL",
    "FIELD_CODE",
    "FIELD_HTTP_STATUS",
    "FIELD_MESSAGE",
    "FIELD_SUBCODE",
    "FIELD_TRACE",
    "FIELD_TYPE",
    "FIELD_USER_MSG",
    "FIELD_USER_TITLE",
    "IG_POSITION_FEED",
    "META_CODE_PARAM",
    "META_ERROR_FIELDS",
    "META_SUBCODE_APP_DEV_MODE",
    "META_SUBCODE_UNSUPPORTED_GET",
    "PLATFORM_INSTAGRAM",
    "REDACTED",
    "TARGET_ADVANTAGE",
    "TARGET_AGE_MAX",
    "TARGET_AGE_MIN",
    "TARGET_AUTOMATION",
    "TARGET_COUNTRIES",
    "TARGET_GEO",
    "TARGET_IG_POSITIONS",
    "TARGET_PLATFORMS",
    "VALIDATE_ONLY",
    "VALIDATE_ONLY_VALUE",
]
