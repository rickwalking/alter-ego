"""Module-level constants for the autopilot bounded context.

Per backend/CLAUDE.md, each context owns its own constants file. State
*values* live on ``AutopilotRunState`` (the single spelling of each state).
Everything else that would otherwise be a magic string lives here.
"""

MODULE_NAME = "autopilot"

# Persistence (docs/architecture/grokbot-autopilot.md §4 + AE-0350).
TABLE_AUTOPILOT_RUNS = "autopilot_runs"
TABLE_TOPIC_CANDIDATES = "topic_candidates"
TABLE_INTEGRATION_CREDENTIALS = "integration_credentials"
TABLE_TELEGRAM_UPDATES = "telegram_updates"

# ``carousel_projects.id`` is VARCHAR(36). The FK column must match that type.
CAROUSEL_PROJECTS_TABLE = "carousel_projects"
CAROUSEL_PROJECT_FK = f"{CAROUSEL_PROJECTS_TABLE}.id"
TOPIC_CANDIDATE_FK = f"{TABLE_TOPIC_CANDIDATES}.id"

INDEX_RUNS_STATE_UPDATED_AT = "idx_autopilot_runs_state_updated_at"
UQ_RUNS_CAROUSEL_PROJECT = "uq_autopilot_runs_carousel_project_id"
UQ_TOPIC_SIGNAL_HASH = "uq_topic_candidates_signal_hash"
FK_RUNS_CAROUSEL_PROJECT = "fk_autopilot_runs_carousel_project_id"
FK_RUNS_TOPIC_CANDIDATE = "fk_autopilot_runs_topic_candidate_id"

ON_DELETE_SET_NULL = "SET NULL"
ON_DELETE_RESTRICT = "RESTRICT"

CAROUSEL_PROJECT_ID_LENGTH = 36
STATE_LENGTH = 32
PROVIDER_LENGTH = 64
STATUS_LENGTH = 64
SIGNAL_HASH_LENGTH = 128
IG_IDENTIFIER_LENGTH = 128

# Transactional outbox (ADR-0004). The family is ``content.autopilot.*``;
# this ticket emits the state-changed member named by the acceptance criteria.
EVENT_TYPE_STATE_CHANGED = "content.autopilot.state_changed"
AGGREGATE_TYPE_AUTOPILOT_RUN = "autopilot_run"
EVENT_VERSION = 1
PAYLOAD_PREVIOUS_STATE = "previous_state"
PAYLOAD_STATE = "state"
PAYLOAD_REASON = "reason"
METADATA_MODULE = "module"

INVALID_TRANSITION_MESSAGE = "invalid_autopilot_transition"

# Service API key (AE-0351). The plaintext key is never stored or logged.
HEADER_API_KEY = "X-Api-Key"
ROUTER_PREFIX = "/autopilot"
PATH_SIGNALS = "/signals"
TAG_AUTOPILOT = "autopilot"
RATE_LIMIT_SCOPE_AUTOPILOT = "autopilot"
DETAIL_API_KEY_INVALID = "invalid_api_key"
DETAIL_API_KEY_UNCONFIGURED = "autopilot_api_key_unconfigured"
LOG_API_KEY_REJECTED = "autopilot_api_key_rejected"
LOG_API_KEY_DISABLED = "autopilot_api_key_disabled"
REASON_KEY_MISSING = "missing"
REASON_KEY_MISMATCH = "mismatch"

# Instagram publish job (AE-0357).
PUBLISH_MAX_ATTEMPTS = 3
PUBLISH_SCAN_LIMIT = 20
CONTAINER_REUSE_HOURS = 24
# Wait after attempt 1, then after attempt 2. The third failure is terminal.
PUBLISH_BACKOFF_SECONDS = (60, 300)
REASON_CAROUSEL_MISSING = "carousel_missing"
REASON_CAROUSEL_NOT_PUBLIC = "carousel_not_public"
REASON_PUBLIC_BASE_URL_MISSING = "instagram_public_base_url_not_configured"
REASON_IG_LOGIN_ABSENT = "instagram_token_missing"
REASON_QUOTA_EXHAUSTED = "content_publishing_limit_exhausted"
REASON_PUBLISHED = "published"
REASON_ATTEMPTS_EXHAUSTED = "publish_attempts_exhausted"
REASON_CONTAINER_MISSING = "instagram_container_missing"
STATE_UNPUBLISHED = "unpublished"
EVENT_TYPE_PUBLISH_NOTICE = "content.autopilot.publish_notice"
PAYLOAD_PERMALINK = "permalink"
PAYLOAD_ERROR_CODE = "error_code"
PAYLOAD_OFFER_RETRY = "offer_retry"
PAYLOAD_RETRY_CALLBACK = "retry_callback"
PAYLOAD_OUTCOME = "outcome"
CALLBACK_RETRY_PREFIX = "ap:retry:"
NOTICE_PUBLISHED = "published"
NOTICE_PUBLISH_FAILED = "publish_failed"
LOG_PUBLISH_JOB = "autopilot_instagram_publish"
