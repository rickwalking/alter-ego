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
