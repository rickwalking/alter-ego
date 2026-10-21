"""Model queue, circuit breaker and LLM alert constants.

Each LLM role can run on a queue of models (``LLM_MODEL_QUEUE_<ROLE>``): the
first model with a closed breaker answers. A breaker opens per model by the
class of its failure, so a quota or a refused model is skipped instantly
instead of being retried. Breaker changes and "all models down" go to a
send-only Telegram alerts bot.

A queue spec is comma-separated ``<transport>:<model id>`` entries, in order.
The breaker defaults are in seconds; the live values come from ``Settings``.
The failure-text markers classify provider errors.
"""

QUEUE_ENTRY_SEPARATOR = ","
QUEUE_TRANSPORT_SEPARATOR = ":"
TRANSPORT_GO = "go"
TRANSPORT_SIDECAR = "sidecar"
SIDECAR_PROVIDER_SEPARATOR = "/"

DEFAULT_BREAKER_FAILURES = 3
DEFAULT_BREAKER_COOLDOWN_SECONDS = 300.0
DEFAULT_BREAKER_MAX_COOLDOWN_SECONDS = 3600.0
DEFAULT_BREAKER_QUOTA_COOLDOWN_SECONDS = 3600.0
DEFAULT_BREAKER_FATAL_COOLDOWN_SECONDS = 21600.0

QUEUE_TRANSIENT_TRIES = 3
QUEUE_THROTTLE_RETRIES = 2
QUEUE_CONTENT_TRIES = 3
QUEUE_BACKOFF_BASE_SECONDS = 2.0
QUEUE_BACKOFF_MAX_SECONDS = 8.0
QUEUE_JITTER_MAX_SECONDS = 1.0
QUEUE_THROTTLE_MIN_SECONDS = 1.0
QUEUE_THROTTLE_MAX_SECONDS = 4.0
QUEUE_RETRY_AFTER_CAP_SECONDS = 30.0

MARKER_FREE_TIER = "FreeTierError"
MARKERS_USAGE_LIMIT = ("UsageLimit", "usage limit")
HEADER_RETRY_AFTER = "retry-after"
STATUS_UNAUTHORIZED = 401
STATUS_FORBIDDEN = 403
STATUS_TOO_MANY_REQUESTS = 429

DEFAULT_SIDECAR_TIMEOUT_SECONDS = 120.0
DEFAULT_SIDECAR_CONCURRENCY = 2
SIDECAR_BASIC_USER = "opencode"
SIDECAR_PATH_SESSION = "/session"
SIDECAR_PATH_MESSAGE = "/session/{session_id}/message"
SIDECAR_PATH_SESSION_ID = "/session/{session_id}"
SIDECAR_SESSION_TITLE = "alter-ego"
SIDECAR_PART_TEXT = "text"
ERR_SIDECAR_EMPTY = "opencode sidecar returned no text"
ERR_SIDECAR_SYNC = "the opencode sidecar model is async-only"
ERR_ALL_MODELS_DOWN = "all LLM models unavailable: {summary}"
ERR_EMPTY_QUEUE = "LLM model queue is empty"

ALERT_ALL_DOWN_MIN_INTERVAL_SECONDS = 900.0
TELEGRAM_SEND_URL = "https://api.telegram.org/bot{token}/sendMessage"
ALERT_TIMEOUT_SECONDS = 10.0
ALERT_OPENED = "🔴 LLM breaker OPEN: {model} ({failure}) for {cooldown}. {reason}"
ALERT_HALF_OPEN = "🟡 LLM breaker half-open: probing {model}"
ALERT_CLOSED = "🟢 LLM breaker closed: {model} is answering again"
ALERT_ALL_DOWN = "🚨 All LLM models unavailable ({role}): {summary}"

LOG_BREAKER_OPENED = "llm_breaker_opened"
LOG_BREAKER_HALF_OPEN = "llm_breaker_half_open"
LOG_BREAKER_CLOSED = "llm_breaker_closed"
LOG_MODEL_SKIPPED = "llm_model_skipped"
LOG_MODEL_RETRY = "llm_queue_retry"
LOG_ALL_MODELS_DOWN = "llm_all_models_down"
LOG_ALERT_FAILED = "llm_alert_failed"
