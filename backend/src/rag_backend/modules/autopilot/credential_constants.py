"""Instagram credential constants.

The access token is never written to a log. The refresh call uses the
unversioned Instagram Login endpoint, not ``META_IG_GRAPH_BASE``.

Without a usable Fernet key or stored row, the manual route uses the legacy env token.
"""

PROVIDER_INSTAGRAM = "instagram"

REFRESH_AFTER_DAYS = 50
EXPIRY_REFRESH_WINDOW_DAYS = 10
EXPIRY_ALERT_WINDOW_DAYS = 7
SEED_LIFETIME_DAYS = 60
SECONDS_PER_DAY = 86400

META_ERROR_INVALID_TOKEN = 190
IG_REFRESH_URL = "https://graph.instagram.com/refresh_access_token"
GRANT_TYPE_IG_REFRESH = "ig_refresh_token"
PARAM_GRANT_TYPE = "grant_type"
GRAPH_ACCESS_PARAM = "access_token"
FIELD_ERROR = "error"
FIELD_CODE = "code"
FIELD_EXPIRES_IN = "expires_in"
IG_REFRESH_TIMEOUT_SECONDS = 15.0
REFRESH_FAILED_MESSAGE = "instagram_token_refresh_failed"

IG_REGENERATION_DOC = (
    "https://developers.facebook.com/docs/instagram-platform/"
    "instagram-api-with-instagram-login/business-login"
)
TEXT_ALERT_EXPIRING = (
    "Instagram token refresh failed and it expires in {days} days. "
    "Generate a new long-lived token by hand: {link}"
)
TEXT_ALERT_INVALID = (
    "Instagram token refresh failed with Meta error {code} (invalid token). "
    "Generate a new long-lived token by hand: {link}"
)
TEXT_ALERT_BOTH = (
    "Instagram token refresh failed with Meta error {code} (invalid token) "
    "and it expires in {days} days. "
    "Generate a new long-lived token by hand: {link}"
)
ALERT_EXPIRING = "expiring"
ALERT_INVALID = "invalid"
ALERT_BOTH = "both"

KEY_PROBLEM_MISSING = "missing"
KEY_PROBLEM_INVALID = "invalid"
PUBLISHING_DISABLED = "disabled"
LOG_CREDENTIALS_KEY_UNUSABLE = "credentials_encryption_key_unusable"
LOG_CREDENTIAL_DECRYPT_FAILED = "instagram_credential_decrypt_failed"
LOG_CREDENTIAL_READ_FAILED = "instagram_credential_read_failed"
LOG_CREDENTIAL_REFRESHED = "instagram_credential_refreshed"
LOG_CREDENTIAL_REFRESH_FAILED = "instagram_credential_refresh_failed"
LOG_CREDENTIAL_SEEDED = "instagram_credential_seeded"
LOG_CREDENTIAL_ALERT_SKIPPED = "instagram_credential_alert_skipped"
LOG_CREDENTIAL_ALERT_FAILED = "instagram_credential_alert_failed"
LOG_CREDENTIAL_ENV_FALLBACK = "instagram_credential_env_fallback"
PUBLISHING_ENV_FALLBACK = "env_token_fallback"
FALLBACK_REASON_KEY_UNUSABLE = "encryption_key_unusable"
FALLBACK_REASON_STORE_UNREADABLE = "credential_store_unreadable"
FALLBACK_REASON_STORE_EMPTY = "credential_store_empty"
