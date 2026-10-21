"""Telegram webhook constants.

Kept beside ``constants.py`` and ``notify_constants.py`` so none of them
exceeds the 400-line limit. The webhook secret is never written to a log.

Retry is refused when the post may already be live. “Fix issues” is queued on the run
row like a rework: the phase slot carries a marker (it fits ``REWORK_PHASE_LENGTH``) and
the worker tick applies it.
"""

HEADER_WEBHOOK_AUTH = "X-Telegram-Bot-Api-Secret-Token"
PATH_TELEGRAM_WEBHOOK = "/telegram/webhook"
TAG_TELEGRAM = "telegram"
APP_STATE_OWNER_ACTIONS = "autopilot_owner_actions"
APP_STATE_ENGINE = "autopilot_engine_factory"
LOG_WEBHOOK = "autopilot_telegram_webhook"
LOG_WEBHOOK_FAILED = "autopilot_telegram_webhook_failed"
LOG_WEBHOOK_REPLY_FAILED = "autopilot_telegram_reply_failed"

KIND_CALLBACK = "callback"
KIND_MESSAGE = "message"
KIND_IGNORED = "ignored"
KIND_APPROVE = "approve"
KIND_REWORK = "rework"
KIND_REJECT = "reject"
KIND_RETRY = "retry"
KIND_PHASE = "phase"
KIND_FIX = "fix"

PHASE_SLUG_TEXT = "text"
PHASE_SLUG_DESIGN = "design"
PHASE_SLUG_IMAGES = "images"
PHASE_SLUG_OUTLINE = "outline"
CALLBACK_PHASE_PREFIX = "ap:rw:"

ANSWER_UNKNOWN = "unknown action"
ANSWER_ALREADY = "already handled"
ANSWER_APPROVED = "Approved"
ANSWER_REJECTED = "Rejected"
ANSWER_RETRY = "Retrying"
TEXT_ALREADY = "already handled"
TEXT_APPROVED = "Approved. Publishing."
TEXT_REJECTED = "Rejected. The carousel stays private."
TEXT_RETRY = "Retrying publish."
ANSWER_MAY_BE_LIVE = "Not retried: the post may already be live"
TEXT_MAY_BE_LIVE = (
    "Not retried: Instagram reports this carousel as published. "
    "Check Instagram before posting it again by hand."
)
TEXT_CHOOSE_PHASE = "Choose what to rework."
TEXT_FORCE_REPLY = "What should change?"
TEXT_REWORKING = "Reworking {phase}."
TEXT_REVISION_CAP = "Revision cap reached."
TEXT_APPROVE_FAILED = "Could not approve."
TEXT_APPROVE_REFUSED = "Could not approve. The review is still open."

REASON_OWNER_APPROVED = "owner_approved"
REASON_OWNER_REJECTED = "owner_rejected"
REASON_OWNER_REWORK = "owner_rework"
REASON_OWNER_RETRY = "owner_retry"
REASON_APPROVE_FAILED = "owner_approve_failed"

REASON_OWNER_AUTOFIX = "owner_autofix"
AUTOFIX_REWORK_PHASE = "owner_autofix"
ANSWER_NOTHING_TO_FIX = "Nothing to fix"
ANSWER_FIXING = "Fixing issues"
TEXT_SUPERSEDED = "Superseded by fixed version. Fixing the issues now."

BUTTON_PHASE_TEXT = "Text"
BUTTON_PHASE_DESIGN = "Design"
BUTTON_PHASE_IMAGES = "Images"
BUTTON_PHASE_OUTLINE = "Outline"

KEY_UPDATE_ID = "update_id"
KEY_CALLBACK_QUERY = "callback_query"
KEY_MESSAGE = "message"
KEY_FROM = "from"
KEY_ID = "id"
KEY_MESSAGE_ID = "message_id"
KEY_DATA = "data"
KEY_CHAT = "chat"
KEY_TEXT = "text"

TELEGRAM_METHOD_ANSWER = "answerCallbackQuery"
TELEGRAM_METHOD_EDIT_TEXT = "editMessageText"
TELEGRAM_METHOD_SET_WEBHOOK = "setWebhook"
FIELD_CALLBACK_QUERY_ID = "callback_query_id"
FIELD_FORCE_REPLY = "force_reply"
FIELD_SELECTIVE = "selective"
FIELD_URL = "url"
FIELD_WEBHOOK_AUTH = "secret_token"
FIELD_ALLOWED_UPDATES = "allowed_updates"
ALLOWED_UPDATE_MESSAGE = "message"
ALLOWED_UPDATE_CALLBACK = "callback_query"
SET_WEBHOOK_EXIT_OK = 0
SET_WEBHOOK_EXIT_FAILED = 1
SET_WEBHOOK_EXIT_USAGE = 2

LEDGER_PENDING = "pending"
LEDGER_PENDING_OWNER = "owner"
LEDGER_PENDING_PHASE = "phase"
REWORK_SCAN_LIMIT = 20

CALLBACK_ACTION_PATTERN = (
    r"^ap:(approve|rework|reject|retry|fix):"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)
CALLBACK_PHASE_PATTERN = (
    r"^ap:rw:(text|design|images|outline):"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)
