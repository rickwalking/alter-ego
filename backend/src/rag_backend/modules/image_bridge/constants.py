"""Constants for the image bridge bounded context (ADR-0022).

Contract and limits: ``docs/architecture/grokbot-image-bridge.md``.

The default image size matches the OpenAI service (``openai_image._DEFAULT_SIZE``).
``secrets.token_urlsafe(32)`` is 43 url-safe characters. Base64 grows by 4/3, so a
longer payload cannot decode to at most ``MAX_IMAGE_BYTES``. Waiter failures are
``RuntimeError``, the same contract as ``OpenAIImageService``.
"""

MODULE_NAME = "image_bridge"


TABLE_IMAGE_BRIDGE_JOBS = "image_bridge_jobs"
INDEX_JOBS_STATUS_EXPIRES_AT = "ix_image_bridge_jobs_status_expires_at"
STATUS_LENGTH = 16
SIZE_LENGTH = 16
TOKEN_SHA256_LENGTH = 64
ERROR_CODE_LENGTH = 128
ERROR_MESSAGE_MAX_CHARS = 2000
JOB_RETENTION_DAYS = 7


DEFAULT_IMAGE_MODEL = "gpt-image-2"
DEFAULT_IMAGE_SIZE = "1536x1024"
SIZE_SEPARATOR = "x"
IMAGE_COUNT = 1
RESPONSE_FORMAT_B64_JSON = "b64_json"
CONTENT_TYPE_CAROUSEL = "carousel"
CALLBACK_TOKEN_BYTES = 32
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_MAX_CONCURRENCY = 2
POLL_INTERVAL_SECONDS = 2.0
WEBHOOK_TIMEOUT_SECONDS = 15.0
DEFAULT_WEBHOOK_AUTH_HEADER = "Authorization"
HEADER_CONTENT_TYPE = "Content-Type"
CONTENT_TYPE_JSON = "application/json"

FIELD_JOB_ID = "job_id"
FIELD_MODEL = "model"
FIELD_PROMPT = "prompt"
FIELD_SIZE = "size"
FIELD_N = "n"
FIELD_RESPONSE_FORMAT = "response_format"
FIELD_CALLBACK_URL = "callback_url"
FIELD_CALLBACK_TOKEN = "callback_token"  # noqa: S105  # integrity-ok: JSON field name, not a secret
FIELD_EXPIRES_AT = "expires_at"
FIELD_METADATA = "metadata"
FIELD_PROJECT_ID = "project_id"
FIELD_CONTENT_TYPE = "content_type"


FIELD_DATA = "data"
FIELD_B64_JSON = "b64_json"
FIELD_ERROR = "error"
FIELD_CODE = "code"
FIELD_TYPE = "type"
FIELD_MESSAGE = "message"

MAX_CALLBACK_BODY_BYTES = 16 * 1024 * 1024
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_B64_CHARS = (MAX_IMAGE_BYTES + 2) // 3 * 4
MIN_IMAGE_SIDE = 512
MAX_IMAGE_SIDE = 4096
ALLOWED_IMAGE_FORMATS = frozenset({"PNG", "JPEG", "WEBP"})
OUTPUT_IMAGE_FORMAT = "PNG"


API_PREFIX = "/api"
ROUTER_PREFIX = "/v1/image-bridge"
PATH_JOB_RESULT = "/jobs/{job_id}/result"
CALLBACK_URL_TEMPLATE = "{base}" + API_PREFIX + ROUTER_PREFIX + PATH_JOB_RESULT
TAG_IMAGE_BRIDGE = "image-bridge"
HEADER_CALLBACK_TOKEN = "X-Image-Bridge-Token"  # noqa: S105  # integrity-ok: header name, not a secret
HEADER_CONTENT_LENGTH = "content-length"
RESPONSE_FIELD_DETAIL = "detail"

DETAIL_ACCEPTED = "accepted"
DETAIL_UNAUTHORIZED = "invalid callback token"
DETAIL_NOT_PENDING = "job is no longer pending"
DETAIL_TOO_LARGE = "callback body too large"
DETAIL_INVALID = "callback body is not a valid ImagesResponse or error"


ERROR_CODE_WEBHOOK_FAILED = "webhook_failed"
ERROR_CODE_MALFORMED = "malformed_callback"
ERROR_CODE_INVALID_IMAGE = "invalid_image"
ERROR_CODE_UNKNOWN = "unknown_error"

ERR_MALFORMED_NOT_OBJECT = "callback body is not a JSON object"
ERR_MALFORMED_ERROR = "callback error is not an object"
ERR_MALFORMED_DATA = "callback data is not a non-empty list"
ERR_MALFORMED_ENTRY = "callback data[0] has no b64_json"
ERR_IMAGE_TOO_LARGE = "image exceeds the decoded size limit"
ERR_IMAGE_NOT_BASE64 = "b64_json is not valid base64"
ERR_IMAGE_UNREADABLE = "image could not be decoded"
ERR_IMAGE_FORMAT = "image format {fmt} is not allowed"
ERR_IMAGE_DIMENSIONS = "image is {width}x{height}; each side must be 512-4096 px"
ERR_INVALID_SIZE = "size {size!r} is not WIDTHxHEIGHT"


ERR_WEBHOOK_STATUS = "Grok Bot webhook answered HTTP {status}"
ERR_WEBHOOK_TRANSPORT = "Grok Bot webhook request failed: {reason}"
ERR_JOB_FAILED = "Grok Bot image job {job_id} failed: {code}"
ERR_JOB_EXPIRED = "Grok Bot image job {job_id} expired after {seconds}s"
ERR_JOB_MISSING = "Grok Bot image job {job_id} disappeared"
ERR_JOB_NO_IMAGE = "Grok Bot image job {job_id} succeeded without image bytes"
ERR_CONFIG_MISSING = "the image bridge needs {names}; set it and retry"
ENV_WEBHOOK_URL = "GROKBOT_IMAGE_WEBHOOK_URL"
ENV_PUBLIC_BASE_URL = "IMAGE_BRIDGE_PUBLIC_BASE_URL"
CONFIG_NAMES_SEPARATOR = ", "
URL_TRAILING_SLASH = "/"


PROVIDER_GROKBOT = "grokbot"
PROVIDER_OPENAI_FALLBACK = "openai_fallback"
PROVIDER_OPENAI = "openai"
LOG_MISCONFIGURED = "image_bridge_misconfigured"
LOG_JOB_STARTED = "image_bridge_job_started"
LOG_JOB_SUCCEEDED = "image_bridge_job_succeeded"
LOG_WEBHOOK_FAILED = "image_bridge_webhook_failed"
LOG_IMAGE_GENERATED = "image_bridge_image_generated"
LOG_FALLBACK = "image_bridge_fallback"
LOG_CALLBACK_REJECTED = "image_bridge_callback_rejected"
LOG_CALLBACK_RECORDED = "image_bridge_callback_recorded"
REASON_MAX_CHARS = 300
REASON_FORMAT = "{kind}: {message}"
