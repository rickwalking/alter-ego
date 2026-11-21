"""Reels list, repost drafts, owner approval and the Reels publish (ADR-0031)."""

from __future__ import annotations

PATH_REELS = "/reels"
PATH_REEL_VIDEO = "/reels/{media_id}/video"
PATH_REPOST = "/repost"
PATH_REPOST_ID = "/repost/{repost_id}"
PATH_REPOSTS = "/reposts"
PATH_PUBLIC_PREFIX = "/r"
PATH_PUBLIC_FILE = "/{repost_id}/{file_name}"
PUBLIC_URL_TEMPLATE = "{base}/r/{repost_id}/{file_name}"
TAG_REPOST_FILES = "repost-files"

FILE_PREVIEW = "preview.mp4"
FILE_COVER = "cover.jpg"
FILE_ORIGINAL_COVER = "original_cover.jpg"
FILE_SOURCE = "source.mp4"
FILE_HOOK_TEXT = "hook.txt"
PUBLIC_FILES: dict[str, str] = {
    FILE_PREVIEW: "video/mp4",
    FILE_COVER: "image/jpeg",
    FILE_ORIGINAL_COVER: "image/jpeg",
}
MEDIA_TYPE_MP4 = "video/mp4"
REPOSTS_DIR_NAME = "reposts"

HEADER_IDEMPOTENCY_KEY = "Idempotency-Key"
IDEMPOTENCY_MIN = 8
IDEMPOTENCY_MAX = 128
IDEMPOTENCY_PATTERN = r"^[A-Za-z0-9_-]{8,128}$"

STATUS_PENDING = "pending_approval"
STATUS_APPROVED = "approved"
STATUS_PROCESSING = "processing"
STATUS_PUBLISHED = "published"
STATUS_FAILED = "failed"
STATUS_REJECTED = "rejected"
STATUS_EXPIRED = "expired"
ALL_STATUSES: frozenset[str] = frozenset({
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_PROCESSING,
    STATUS_PUBLISHED,
    STATUS_FAILED,
    STATUS_REJECTED,
    STATUS_EXPIRED,
})
LIVE_STATUSES: tuple[str, ...] = (
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_PROCESSING,
    STATUS_PUBLISHED,
)
SERVED_STATUSES: frozenset[str] = frozenset({
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_PROCESSING,
    STATUS_PUBLISHED,
    STATUS_FAILED,
})
CAP_STATUSES: tuple[str, ...] = (
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_PROCESSING,
    STATUS_PUBLISHED,
    STATUS_REJECTED,
    STATUS_EXPIRED,
)

COVER_GROK = "grok"
COVER_ORIGINAL = "original"

ACTOR_OWNER_PREFIX = "owner:"
ACTOR_WORKER = "worker"

MIN_AGE_DAYS = 60
REPOST_WINDOW_DAYS = 90
WEEKLY_CAP = 2
WEEK_DAYS = 7
APPROVAL_TTL_HOURS = 12
CAPTION_EDIT_TTL_MINUTES = 15
CAPTION_MAX = 2200
HASHTAGS_MAX = 30
MENTIONS_MAX = 20
HOOK_TEXT_MAX = 90
HOOK_DURATION_DEFAULT = 2.5
HOOK_DURATION_MAX = 4.0
FINAL_MIN_SECONDS = 3.0
FINAL_MAX_SECONDS = 90.0
REASON_MIN = 10
REASON_MAX = 600
COLLABORATORS_MAX = 3
MEDIA_ID_MAX = 32
USERNAME_PATTERN = r"^[A-Za-z0-9._]{1,30}$"
HASHTAG_PATTERN = r"(?<![\w&])#\w+"
MENTION_PATTERN = r"(?<![\w.])@[A-Za-z0-9._]+"
LIST_DEFAULT = 20
LIST_MAX = 100

ERR_INVALID_FIELD = "invalid_field"
ERR_REEL_NOT_FOUND = "reel_not_found"
ERR_REPOST_NOT_FOUND = "repost_not_found"
ERR_ALREADY_REPOSTED = "already_reposted"
ERR_IDEMPOTENCY_CONFLICT = "idempotency_conflict"
ERR_TOO_RECENT = "too_recent"
ERR_ASSET_INVALID = "asset_invalid"
ERR_WEEKLY_CAP = "weekly_cap_reached"
ERR_RATE_LIMITED = "rate_limited"
ERR_UNAVAILABLE = "instagram_unavailable"
ERR_RENDER_FAILED = "render_failed"
ERR_RENDER_UNAVAILABLE = "render_unavailable"
ERR_RENDER_TOO_LARGE = "render_too_large"
ERR_RENDER_DURATION = "render_duration_invalid"
ERR_SOURCE_UNAVAILABLE = "source_unavailable"
ERR_CONTAINER_TIMEOUT = "container_timeout"
ERR_CONTAINER_ERROR = "container_error"
ERR_PUBLISH_FAILED = "publish_failed"
ERR_NOT_CONFIGURED = "instagram_not_configured"

HTTP_OK = 200
HTTP_ACCEPTED = 202
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_UNPROCESSABLE = 422
HTTP_UNAVAILABLE = 503

MESSAGE_BY_CODE: dict[str, str] = {
    ERR_INVALID_FIELD: "Validation failed.",
    ERR_REEL_NOT_FOUND: "Not one of the account's Reels.",
    ERR_REPOST_NOT_FOUND: "No repost with this id.",
    ERR_ALREADY_REPOSTED: "This Reel was reposted or has a pending repost.",
    ERR_IDEMPOTENCY_CONFLICT: "Idempotency-Key reused with a different body.",
    ERR_TOO_RECENT: "The Reel is younger than 60 days.",
    ERR_ASSET_INVALID: "The cover asset is missing, expired, used or not a reel cover.",
    ERR_WEEKLY_CAP: "Two repost drafts were already created in the last 7 days.",
    ERR_UNAVAILABLE: "Instagram could not be reached.",
    ERR_NOT_CONFIGURED: "Instagram is not configured.",
    ERR_SOURCE_UNAVAILABLE: (
        "Instagram does not share this Reel's video (usually licensed audio), "
        "so it cannot be reposted."
    ),
    ERR_RENDER_FAILED: "ffmpeg could not render the preview.",
    ERR_RENDER_UNAVAILABLE: "ffmpeg is not available on the server.",
    ERR_RENDER_TOO_LARGE: "The rendered video is over 100 MB.",
    ERR_RENDER_DURATION: "The rendered video does not last 3-90 s.",
}

FIELD_IDEMPOTENCY = "Idempotency-Key"
FIELD_BODY = "body"
FIELD_MEDIA_ID = "media_id"
FIELD_CAPTION = "caption"
FIELD_HOOK_TEXT = "hook_text"
FIELD_HOOK_DURATION = "hook_duration_s"
FIELD_TRIM_START = "trim_start_s"
FIELD_TRIM_END = "trim_end_s"
FIELD_COVER_ASSET = "cover.asset_id"
FIELD_COLLABORATORS = "collaborators"
FIELD_REASON = "reason"
FIELD_WINDOW_EARLIEST = "publish_window.earliest"
FIELD_WINDOW_LATEST = "publish_window.latest"
FIELD_STATUS = "status"
FIELD_SINCE = "since"
FIELD_LIMIT = "limit"

CALLBACK_OK = "ok"
CALLBACK_ORIGINAL = "orig"
CALLBACK_CAPTION = "cap"
CALLBACK_NO = "no"
CALLBACK_PREFIX = "ap:rp:"
CALLBACK_PATTERN = (
    r"^ap:rp:(ok|orig|cap|no):"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)

BUTTON_APPROVE = "✅ Aprovar"
BUTTON_ORIGINAL = "🖼 Usar capa original"
BUTTON_CAPTION = "✏️ Editar legenda"
BUTTON_REJECT = "❌ Rejeitar"
ANSWER_APPROVED = "Aprovado"
ANSWER_REJECTED = "Rejeitado"
ANSWER_CAPTION = "Envie a nova legenda"
ANSWER_GONE = "Este repost não está mais aguardando"
TEXT_CAPTION_PROMPT = "Envie a nova legenda do repost (até 2200 caracteres)."
TEXT_CAPTION_INVALID = "Legenda recusada ({field}). Envie outra."
TEXT_HEADER = "🔁 Repost de Reel para aprovar"
TEXT_ORIGINAL = "Original: {permalink}"
TEXT_METRICS = (
    "Views {views} · Alcance {reach} · Curtidas {likes} · Comentários {comments}\n"
    "Salvos {saved} · Compartilhamentos {shares} · Seguidores {follows}"
)
TEXT_HOOK = "Gancho: {hook}"
TEXT_SOURCE = "Fonte do vídeo: {width}x{height}"
TEXT_SOURCE_LOW = (
    "⚠️ Fonte do vídeo: {width}x{height}. O Instagram só entrega esta versão em baixa "
    "qualidade, então o repost sai borrado."
)
SOURCE_LOW_HEIGHT = 720
TEXT_REASON = "Motivo: {reason}"
TEXT_WINDOW = "Janela: {earliest} → {latest}"
TEXT_CAPTION = "Legenda:\n{caption}"
TEXT_PREVIEW_LINK = "Prévia: {url}"
TEXT_EXPIRES = "Expira em 12 h."
TEXT_PREVIEW_CAPTION = "Prévia do repost (gancho e corte aplicados)"
TEXT_COVER_CAPTION = "Capa nova do repost"
TEXT_DECIDED_APPROVED = "✅ Aprovado. Publica {when}. Capa: {cover}."
TEXT_DECIDED_REJECTED = "❌ Repost rejeitado."
TEXT_DECIDED_EXPIRED = "⌛ Repost expirado sem resposta."
TEXT_PUBLISHED = "🔁 Repost publicado: {permalink}"
TEXT_FAILED = "⚠️ Repost falhou ({code})."
TEXT_NOW = "agora"
TEXT_UNKNOWN = "—"
TELEGRAM_CAPTION_MAX = 1024
TELEGRAM_VIDEO_MAX_BYTES = 49 * 1024 * 1024
TELEGRAM_METHOD_VIDEO = "sendVideo"
TELEGRAM_FIELD_VIDEO = "video"
TELEGRAM_FIELD_SUPPORTS_STREAMING = "supports_streaming"
TELEGRAM_UPLOAD_TIMEOUT_SECONDS = 120.0

TABLE_REPOSTS = "autopilot_reposts"
TABLE_REEL_FACTS = "autopilot_reel_facts"
INDEX_REPOSTS_MEDIA = "ix_autopilot_reposts_media_created"
INDEX_REPOSTS_STATUS = "ix_autopilot_reposts_status"
UQ_REPOSTS_KEY = "uq_autopilot_reposts_idempotency_key"
KEY_LENGTH = 128
HASH_LENGTH = 64
STATUS_LENGTH = 24
COVER_CHOICE_LENGTH = 16
CODE_LENGTH = 64
ERROR_MESSAGE_LENGTH = 500
PERMALINK_LENGTH = 512
ACTOR_LENGTH = 64
ADVISORY_LOCK_REPOST = 7_310_031

RENDER_WIDTH = 1080
RENDER_HEIGHT = 1920
RENDER_FPS = 30
RENDER_MAX_BYTES = 100 * 1024 * 1024
RENDER_MAXRATE = "6M"
RENDER_BUFSIZE = "12M"
RENDER_CRF = "20"
RENDER_PRESET = "medium"
RENDER_AUDIO_BITRATE = "128k"
RENDER_AUDIO_RATE = "44100"
RENDER_THREADS = "2"
RENDER_TIMEOUT_SECONDS = 600.0
PROBE_TIMEOUT_SECONDS = 20.0
HOOK_FONT_SIZE = 72
HOOK_FONT_FILE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
HOOK_LINE_FILE = "hook_{index}.txt"
HOOK_LINE_CHARS = 22
HOOK_TOP_RATIO = "0.16"
HOOK_BOX_ALPHA = "0.6"
HOOK_BOX_BORDER = 28
HOOK_LINE_SPACING = 12
DOWNLOAD_TIMEOUT_SECONDS = 120.0
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
DOWNLOAD_MAX_BYTES = 500 * 1024 * 1024

CONTAINER_TIMEOUT_MINUTES = 30
CONTAINER_FINISHED = "FINISHED"
CONTAINER_ERROR = "ERROR"
CONTAINER_EXPIRED = "EXPIRED"
CONTAINER_PUBLISHED = "PUBLISHED"
TICK_RENDER_LIMIT = 1
TICK_PUBLISH_LIMIT = 2
TICK_SCAN = 20

GRAPH_MEDIA_TYPE_REELS = "REELS"
GRAPH_FIELD_MEDIA_TYPE = "media_type"
GRAPH_FIELD_VIDEO_URL = "video_url"
GRAPH_FIELD_CAPTION = "caption"
GRAPH_FIELD_COVER_URL = "cover_url"
GRAPH_FIELD_SHARE_TO_FEED = "share_to_feed"
GRAPH_FIELD_COLLABORATORS = "collaborators"
GRAPH_FIELD_CREATION_ID = "creation_id"
GRAPH_FIELD_STATUS_CODE = "status_code"
GRAPH_FIELD_STATUS = "status"
GRAPH_FIELD_PERMALINK = "permalink"
GRAPH_PATH_MEDIA = "/{ig_user_id}/media"
GRAPH_PATH_MEDIA_PUBLISH = "/{ig_user_id}/media_publish"
GRAPH_PATH_OBJECT = "/{object_id}"
GRAPH_PATH_COLLABORATORS = "/{media_id}/collaborators"
GRAPH_FIELD_USERNAME = "username"
GRAPH_DEADLINE_SECONDS = 30.0
GRAPH_TRUE = "true"
GRAPH_FALSE = "false"

LOG_REPOST = "autopilot.repost"
LOG_CREATED = "created"
LOG_RENDERED = "rendered"
LOG_RENDER_FAILED = "render_failed"
LOG_NOTIFIED = "notified"
LOG_NOTIFY_FAILED = "notify_failed"
LOG_EXPIRED = "expired"
LOG_DECIDED = "decided"
LOG_PROCESSING = "processing"
LOG_PUBLISHED = "published"
LOG_PUBLISH_FAILED = "publish_failed"
LOG_TICK_FAILED = "tick_failed"

NO_STORE_HEADERS: dict[str, str] = {"Cache-Control": "no-store"}

__all__ = [name for name in dir() if name.isupper()]
