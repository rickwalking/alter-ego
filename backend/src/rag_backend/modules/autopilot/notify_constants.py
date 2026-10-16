"""Telegram owner-notice constants (AE-0355).

Kept beside ``constants.py`` so neither file exceeds the 400-line limit.
The bot token is never written to a log.
"""

from rag_backend.modules.autopilot.constants import (
    EVENT_TYPE_PUBLISH_NOTICE,
    EVENT_TYPE_READY_FOR_OWNER,
    EVENT_TYPE_STATE_CHANGED,
)

# Telegram owner notices (AE-0355). The bot token is never written to a log.
REASON_NOTIFIER_UNCONFIGURED = "notifier_unconfigured"
EVENT_TYPE_IG_EXPIRING = "content.autopilot.ig_token_expiring"
PAYLOAD_REVISION = "revision"
PAYLOAD_PERSONA_SCORE = "persona_score"
PAYLOAD_SOURCES_COUNT = "sources_count"
PAYLOAD_DAYS_REMAINING = "days_remaining"
LOG_NOTIFIER = "autopilot_telegram_notifier"
LOG_NOTIFIER_UNCONFIGURED = "autopilot_notifier_unconfigured"
LOG_NOTIFIER_FAILED = "autopilot_telegram_send_failed"
LOG_NOTIFIER_DROPPED = "autopilot_telegram_notice_dropped"
TELEGRAM_API_HOST = "https://api.telegram.org"
TELEGRAM_METHOD_MEDIA_GROUP = "sendMediaGroup"
TELEGRAM_METHOD_MESSAGE = "sendMessage"
TELEGRAM_METHOD_PHOTO = "sendPhoto"
TELEGRAM_HTTP_TIMEOUT_SECONDS = 30.0
TELEGRAM_STATUS_RATE_LIMITED = 429
TELEGRAM_RATE_LIMIT_TRIES = 3
TELEGRAM_RETRY_AFTER_DEFAULT = 1.0
TELEGRAM_RETRY_AFTER_CAP_SECONDS = 60.0
TELEGRAM_PHOTO_MIME = "image/jpeg"
TELEGRAM_ALBUM_MIN = 2
NOTIFY_MAX_ATTEMPTS = 3
NOTIFY_BATCH = 5
OUTBOX_SCAN_LIMIT = 100
REMINDER_AFTER_HOURS = 24
REMINDER_SCAN_LIMIT = 20
CAPTION_PREVIEW_CHARS = 1000
CALLBACK_DATA_MAX_BYTES = 64
CALLBACK_APPROVE_PREFIX = "ap:approve:"
CALLBACK_REWORK_PREFIX = "ap:rework:"
CALLBACK_REJECT_PREFIX = "ap:reject:"
# AE-0367: deterministic content repair of the reviewed carousel.
CALLBACK_FIX_PREFIX = "ap:fix:"
PERSONA_SCORE_FORMAT = ".0f"
PATH_OWNER_UI = "/dashboard/create"
BUTTON_APPROVE = "\u2705 Approve"
BUTTON_REWORK = "\u270f\ufe0f Rework"
BUTTON_REJECT = "\U0001f5d1 Reject"
BUTTON_RETRY = "\U0001f501 Retry"
BUTTON_FIX = "\U0001f6e0 Fix issues"
# AE-0367: quality issues listed under the review caption preview.
ISSUES_HEADER = "\u26a0\ufe0f Issues:"
ISSUE_BULLET = "\u2022 {line}"
ISSUES_SEPARATOR = "\n\n"
LOG_REVIEW_ISSUES_FAILED = "autopilot_review_issues_failed"
LABEL_PERSONA = "Persona:"
LABEL_SOURCES = "sources"
# AE-0364: a run with no persona has no scores; the owner sees it on the review.
LABEL_PERSONA_NOT_SCORED = "not scored"
CAPTION_TEMPLATE = "{title}\n{persona} {score} \u00b7 {sources} {sources_label}"
TEXT_CAPTION_MISSING = "Review the slides above."
TEXT_ESCALATED = "Escalated: {reason}"
TEXT_ESCALATED_WITH_LINK = "Escalated: {reason}\n{link}"
# AE-0401: the escalation detail goes between the reason and the link.
TEXT_ESCALATED_DETAIL = "{reason}\n{detail}"
TEXT_FAILED = "Failed: {reason}"
TEXT_PUBLISH_FAILED = "\u274c publish failed: {reason}"
TEXT_PUBLISHED_MEDIA_UNKNOWN = (
    "\u26a0\ufe0f Instagram reports this carousel as published, but the post "
    "could not be matched. The post may already be live; check Instagram. "
    "Retry is off so it is not posted twice."
)
TEXT_REMINDER = "This review has been waiting for more than 24 hours."
TEXT_IG_EXPIRY_DAYS = "Instagram token expires in {days} days."
TEXT_IG_EXPIRY = "Instagram token is expiring."
KIND_REVIEW = "review"
KIND_ESCALATED = "escalated"
KIND_FAILED = "failed"
KIND_PUBLISHED = "published"
KIND_PUBLISH_FAILED = "publish_failed"
KIND_IG_EXPIRING = "ig_token_expiring"
KIND_REMINDER = "reminder"
# QA r1: 72 h owner expiry and a review reopened without regeneration.
KIND_EXPIRED = "expired"
KIND_REVIEW_REOPENED = "review_reopened"
TEXT_EXPIRED = "Review expired after 72 hours. The carousel stays private."
TEXT_REVIEW_REOPENED = "The review is open again ({reason})."
# QA r2 R1: an escalated run closed by the runner (72 h, or carousel rejected).
KIND_ESCALATION_CLOSED = "escalation_closed"
TEXT_ESCALATION_CLOSED = "Escalation closed ({reason}). The carousel stays private."
# QA r3 Q2: a publish held by an unfinished Instagram container.
KIND_PUBLISH_HELD = "publish_held"
TEXT_PUBLISH_HELD = (
    "\u23f3 Instagram publish has been held for over {minutes} minutes by an "
    "unfinished container. It resumes on its own once Instagram reports it."
)
LEDGER_IDS = "ids"
LEDGER_REVIEWS = "reviews"
LEDGER_ALBUM = "album"
LEDGER_KEYBOARD = "keyboard"
LEDGER_REMINDERS = "reminders"
LEDGER_STATUSES = "statuses"
LEDGER_ATTEMPTS = "attempts"
ATTEMPT_REVIEW_PREFIX = "review:"
ATTEMPT_STATUS_PREFIX = "status:"
ATTEMPT_REMINDER_PREFIX = "reminder:"
FIELD_CHAT_ID = "chat_id"
FIELD_MEDIA = "media"
FIELD_CAPTION = "caption"
FIELD_TEXT = "text"
FIELD_REPLY_MARKUP = "reply_markup"
FIELD_INLINE_KEYBOARD = "inline_keyboard"
FIELD_CALLBACK_DATA = "callback_data"
FIELD_TYPE = "type"
FIELD_OK = "ok"
FIELD_RESULT = "result"
FIELD_MESSAGE_ID = "message_id"
FIELD_PARAMETERS = "parameters"
FIELD_RETRY_AFTER = "retry_after"
MEDIA_TYPE_PHOTO = "photo"
ATTACH_SCHEME = "attach://"
FILE_FIELD_PREFIX = "slide"
DETAIL_TRANSPORT = "telegram_transport_error"
DETAIL_HTTP_STATUS = "telegram_http_{status}"
DETAIL_NOT_OK = "telegram_not_ok"
DETAIL_BAD_RESPONSE = "telegram_bad_response"
DETAIL_RATE_LIMITED = "telegram_rate_limited"
DETAIL_CALLBACK_TOO_LONG = "callback_data_exceeds_64_bytes"
NOTIFY_EVENT_TYPES = (
    EVENT_TYPE_READY_FOR_OWNER,
    EVENT_TYPE_STATE_CHANGED,
    EVENT_TYPE_PUBLISH_NOTICE,
    EVENT_TYPE_IG_EXPIRING,
)
