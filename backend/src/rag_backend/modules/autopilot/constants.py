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

# Signal bundle (AE-0352, architecture §5 and §5.1).
SOURCE_X_SEARCH = "x_search"
SOURCE_HN = "hn"
SOURCE_HF_PAPERS = "hf_papers"
SOURCE_RSS = "rss"
SOURCE_BLUESKY = "bluesky"
SOURCE_GITHUB = "github"
ERROR_TIMEOUT = "timeout"
ERROR_FAILED = "failed"
LOG_COLLECTOR_FAILED = "autopilot_collector_failed"
LOG_COLLECTOR_TIMEOUT = "autopilot_collector_timeout"
LOG_UPSTREAM_SKIPPED = "autopilot_upstream_skipped"
APP_STATE_SIGNALS = "autopilot_signals"
COLLECTOR_TIMEOUT_SECONDS = 20.0
SIGNAL_CACHE_TTL_SECONDS = 30 * 60
MAX_SIGNALS = 200
HTTP_TIMEOUT_SECONDS = 10.0
MAX_SIGNAL_TEXT_CHARS = 2000
HTTP_SUCCESS_MIN = 200
HTTP_SUCCESS_MAX = 300
NO_RESULTS_MARK = "No results found"

# X via web search. The backend never requests x.com (architecture §5.1).
X_RESOLVER_NONE = "none"
X_RESOLVER_MIRROR = "mirror"
X_SEARCH_TIMELIMIT = "d"
X_SEARCH_MAX_RESULTS = 10
X_MAX_QUERIES_PER_RUN = 6
X_QUERY_SPACING_MIN_SECONDS = 2.0
X_QUERY_SPACING_MAX_SECONDS = 5.0
X_MAX_AGE_HOURS = 48
X_RESOLVE_TIMEOUT_SECONDS = 3.0
X_CANONICAL_ORIGIN = "https://x.com"
SCHEME_HTTPS = "https"
TWITTER_SNOWFLAKE_EPOCH_MS = 1_288_834_974_657
X_STATUS_URL_PATTERN = r"^https://(x|twitter)\.com/([A-Za-z0-9_]{1,15})/status/(\d+)$"
X_SEARCH_QUERIES = (
    'site:x.com "AI agent"',
    'site:x.com "new model" launch',
    "site:x.com Claude OR GPT OR Gemini OR Grok",
)

# Hacker News Algolia. ``points>100`` matches the architecture table.
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
HN_TAG_STORY = "story"
HN_MIN_POINTS = 100
HN_LOOKBACK_HOURS = 48
HN_ITEM_URL_PREFIX = "https://news.ycombinator.com/item?id="
HN_SEARCH_QUERIES = ("AI", "LLM", "Claude", "GPT", "Gemini", "Grok")
HN_PARAM_TAGS = "tags"
HN_PARAM_QUERY = "query"
HN_PARAM_NUMERIC_FILTERS = "numericFilters"
HN_FILTER_POINTS = "points"
HN_FILTER_CREATED = "created_at_i"

# Hugging Face daily papers.
HF_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"
HF_PAPER_URL_PREFIX = "https://huggingface.co/papers/"

# RSS / Atom. Anthropic publishes no RSS (rss.xml and news/rss.xml were
# HTTP 404 on 2026-10-13); the news sitemap is the machine-readable
# substitute and only ``/news/`` URLs are kept. ai.meta.com/blog RSS was
# also 404; Meta's engineering ML feed is the live official substitute.
FEED_URL_OPENAI = "https://openai.com/news/rss.xml"
FEED_URL_ANTHROPIC = "https://www.anthropic.com/sitemap.xml"
FEED_URL_GOOGLE_AI = "https://blog.google/innovation-and-ai/technology/ai/rss/"
FEED_URL_META_AI = "https://engineering.fb.com/category/ml-applications/feed/"
FEED_URL_VERGE_AI = "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
ANTHROPIC_NEWS_PATH = "/news/"
RSS_MAX_AGE_DAYS = 14

# Bluesky public AppView. ``link`` is often a path, so the collector
# prefixes ``BSKY_ORIGIN`` when the value is relative.
BSKY_TRENDS_URL = "https://public.api.bsky.app/xrpc/app.bsky.unspecced.getTrends"
BSKY_ORIGIN = "https://bsky.app"
BSKY_TREND_LIMIT = "10"
BSKY_PARAM_LIMIT = "limit"

# GitHub Search API. The token is optional; an empty token sends no
# Authorization header.
GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_LOOKBACK_DAYS = 7
GITHUB_TOPIC_QUERY = "topic:llm"
GITHUB_CREATED_PREFIX = "created:>"
GITHUB_SORT_STARS = "stars"
GITHUB_ORDER_DESC = "desc"
GITHUB_PARAM_Q = "q"
GITHUB_PARAM_SORT = "sort"
GITHUB_PARAM_ORDER = "order"
GITHUB_ACCEPT = "application/vnd.github+json"
HEADER_ACCEPT = "Accept"
HEADER_AUTHORIZATION = "Authorization"
HEADER_USER_AGENT = "User-Agent"
HTTP_USER_AGENT = "alter-ego-autopilot"
AUTH_BEARER_PREFIX = "Bearer "

# Topic intake (AE-0353). The scout posts 1-3 proposals. Code decides
# which of them become queued runs.
PATH_TOPICS = "/topics"
# Grok Bot browser observations (AE-0360). Stored beside the allowlist.
PATH_X_SIGNALS = "/x-signals"
PATH_SCOUT_FAILED = "/scout-failed"
SOURCE_X_BROWSER = "x_browser"
TABLE_X_SIGNALS = "autopilot_x_signals"
APP_STATE_SCOUT_NOTIFIER = "autopilot_scout_notifier"
X_POST_TEXT_MAX_CHARS = 600
METRIC_MIN = 0
X_HANDLE_MAX_CHARS = 15
X_SIGNAL_BATCH_MIN = 1
X_SIGNAL_BATCH_MAX = 30
SCOUT_REASON_MAX_CHARS = 500
SCOUT_FAILED_PREFIX = "Scout failed: "
REASON_NOT_STATUS_URL = "not_status_url"
REASON_STALE_STATUS = "stale_status"
REASON_EMPTY_HANDLE = "empty_handle"
REASON_HANDLE_MISMATCH = "handle_mismatch"
DETAIL_SCOUT_NOTIFY_UNCONFIGURED = "scout_notify_unconfigured"
DETAIL_SCOUT_NOTIFY_FAILED = "scout_notify_failed"
DETAIL_SCOUT_REASON_EMPTY = "scout_reason_empty"
LOG_X_SIGNALS = "autopilot_x_signals"
LOG_SCOUT_FAILED = "autopilot_scout_failed"
TABLE_SERVED_SIGNAL_URLS = "autopilot_served_urls"
INDEX_SERVED_URLS_SERVED_AT = "idx_autopilot_served_urls_served_at"
APP_STATE_CLOCK = "autopilot_clock"
LOG_TOPIC_INTAKE = "autopilot_topic_intake"

TEXT_MIN_CHARS = 1
TITLE_MAX_CHARS = 120
ANGLE_MAX_CHARS = 300
WHY_VIRAL_MAX_CHARS = 300
AUDIENCE_MAX_CHARS = 120
NICHE_MAX_CHARS = 80
BRIEF_MAX_CHARS = 800
TOPIC_BATCH_MIN = 1
TOPIC_BATCH_MAX = 3
SOURCE_URL_MIN = 1
SOURCE_URL_MAX = 8
# Longest accepted URL in a topic source or an X observation (QA r1).
URL_MAX_CHARS = 300
SCORE_MIN = 0
SCORE_MAX = 100

SERVED_URL_TTL_HOURS = 6
TOPIC_LOOKBACK_DAYS = 60
JACCARD_DUPLICATE_THRESHOLD = 0.6
DAILY_CAP_TIMEZONE = "America/Sao_Paulo"
DEFAULT_DAILY_CAP = 1
NO_QUEUE_SLOTS = 0

REASON_SOURCE_NOT_IN_SIGNALS = "source_not_in_signals"
REASON_DUPLICATE_TOPIC = "duplicate_topic"
REASON_DAILY_CAP_REACHED = "daily_cap_reached"
REASON_URL_IN_TEXT = "url_in_text"
REASON_EMPTY_TEXT = "empty_text"
STATUS_CANDIDATE_ACCEPTED = "accepted"
KIND_NEW = "new"
KIND_EXISTING = "existing"

HASH_FIELD_SEPARATOR = "\n"
TEXT_ENCODING = "utf-8"
UNICODE_CATEGORY_CONTROL = "Cc"
URL_IN_TEXT_PATTERN = r"(?i)(?:[a-z][a-z0-9+.-]*://|www\.)"
SOURCE_URL_PATTERN = r"(?i)^https?://\S+$"
WORD_PATTERN = r"[^\W_]+"
SOURCE_URL_INVALID = "source_must_be_http_url"
RUN_ATTEMPTS_INITIAL = 0

# Autopilot runner (AE-0354). Phase ids match the editorial workflow.
GATE_RESEARCH = "research"
GATE_OUTLINE = "outline"
GATE_CONTENT = "content"
GATE_DESIGN = "design"
GATE_IMAGES = "images"
GATE_FINAL_REVIEW = "final_review"
PHASE_STATUS_AWAITING = "awaiting_human"
PHASE_STATUS_FAILED = "failed"
PHASE_STATUS_IN_PROGRESS = "in_progress"

EVENT_TYPE_READY_FOR_OWNER = "content.autopilot.ready_for_owner"
AGENT_NAME_AUTOPILOT = "autopilot"
CONTENT_TYPE_CAROUSEL = "carousel"
LANGFUSE_FIELD_CONTENT_TYPE = "content_type"
LANGFUSE_FIELD_AGENT_NAME = "agent_name"
LANGFUSE_FIELD_PHASE = "phase"
LANGFUSE_FIELD_PROJECT_ID = "project_id"
PAYLOAD_PROJECT_ID = "project_id"

LANGUAGE_PT_BR = "pt-BR"
AUTOPILOT_SLIDES_CONFIG = "1 intro, 3 content, 1 closing, 1 cta"
MAX_SLIDES = 10
MIN_RESEARCH_SOURCES = 3
MAX_REVISES_PER_PHASE = 2
MAX_START_ATTEMPTS = 3
RUNS_PER_TICK = 1

REASON_PERSONA_SCORE = "persona_score_below_threshold"
REASON_RESEARCH = "research_sources_insufficient"
REASON_OUTLINE = "outline_slide_count_mismatch"
REASON_FORBIDDEN = "forbidden_phrase"
REASON_DESIGN = "presentation_validation_blocked"
REASON_IMAGES = "image_assets_invalid"
REASON_PHASE_FAILED = "phase_failed"
REASON_RUN_STALE = "run_stale"
REASON_REVISION_CAP = "revision_cap_exceeded"
REASON_START_FAILED = "start_failed"
REASON_READY = "ready_for_owner"
REASON_GENERATING = "generating"
REASON_OWNER_UNCONFIGURED = "owner_unconfigured"
REASON_TOPIC_MISSING = "topic_missing"
REASON_PROJECT_MISSING = "project_missing"
REASON_UNEXPECTED_PHASE = "unexpected_phase"
REASON_PASSED = "passed"
REASON_WAITING = "waiting"

PROMPT_DOMAIN_AUTOPILOT = "autopilot"
PROMPT_REVISE_FEEDBACK = "revise_feedback"
PROMPT_VERSION_V1 = "v1"
VAR_PHASE = "phase"
VAR_REASON = "reason"
VAR_DETAIL = "detail"

FIELD_RESEARCH = "research_findings"
FIELD_CONTENT = "content"
FIELD_SUMMARY = "summary"
FIELD_KEY_POINTS = "key_points"
FIELD_OUTLINE = "outline"
FIELD_PERSONA_SCORES = "persona_scores"
FIELD_OVERALL = "overall"
FIELD_FORBIDDEN_HITS = "forbidden_phrase_hits"
FIELD_FORBIDDEN_PHRASES = "forbidden_phrases"
FIELD_SLIDE_DRAFTS = "slide_drafts"
FIELD_CONTENT_GATE = "content_gate_validation"
FIELD_PRESENTATION_VALIDATION = "presentation_validation"
FIELD_BLOCKING = "blocking"
FIELD_VIOLATIONS = "violations"
FIELD_SEVERITY = "severity"
FIELD_CODE = "code"
FIELD_IMAGE_ASSETS = "image_assets"
FIELD_REVISION_COUNT = "revision_count"
FIELD_CURRENT_PHASE = "current_phase"
FIELD_PHASE_STATUS = "phase_status"
SEVERITY_BLOCKER = "blocker"
BLOCKER_MISSING = "missing_presentation_validation"
BLOCKER_BLOCKING = "blocking"
SOURCE_FIELD_TITLE = "title"
SOURCE_FIELD_TYPE = "source_type"
LOG_RUNNER = "autopilot_runner"
REVIEWER_UNSET = ""
