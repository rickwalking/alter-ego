"""Run-recovery and manual-publish constants (AE-0348 QA round 1).

Kept beside ``constants.py`` so neither file exceeds the 400-line limit.
"""

from __future__ import annotations

# Engine errors the runner did not classify end the run with a reason
# instead of rolling back the whole worker tick on every retry.
REASON_ENGINE_ERROR = "engine_error"
REASON_ENGINE_ERROR_FORMAT = "{prefix}:{kind}:{detail}"
ENGINE_ERROR_DETAIL_MAX_CHARS = 160

# Design revises at most once (architecture §6); other gates twice.
MAX_REVISES_DESIGN = 1

# Owner review expiry (architecture §3, §4): 72 hours in ``awaiting_owner``.
OWNER_REVIEW_EXPIRY_HOURS = 72
REASON_OWNER_EXPIRED = "owner_review_expired"
EXPIRY_SCAN_LIMIT = 20

# Escalated runs whose carousel came back to final review.
REASON_OWNER_FIXED = "owner_fixed_in_web_ui"
ESCALATED_SCAN_LIMIT = 5

# Owner rework is queued by the webhook and applied by the runner.
REASON_REWORK_QUEUED = "owner_rework_queued"
REASON_REWORK_RETRY = "owner_rework_not_applied"
REASON_APPROVE_REFUSED = "owner_approve_refused"

# Manual Instagram publish ledger (non-autopilot carousels) and refusals.
TABLE_MANUAL_PUBLISHES = "instagram_manual_publishes"
FK_MANUAL_PUBLISH_PROJECT = "fk_instagram_manual_publishes_carousel_project"
ON_DELETE_CASCADE = "CASCADE"
REWORK_PHASE_LENGTH = 32
MANUAL_STATE_PUBLISHING = "publishing"
MANUAL_STATE_PUBLISHED = "published"
MANUAL_STATE_FAILED = "failed"
MANUAL_CLAIM_STALE_MINUTES = 10
ERR_AUTOPILOT_RUN_ACTIVE = "autopilot_run_not_publishing"
ERR_PUBLISH_IN_PROGRESS = "instagram_publish_in_progress"

# Review reopened without regeneration: the keyboard is sent again.
REASON_REVIEW_REOPENED = "review_reopened"
LOG_RUNNER_ENGINE_ERROR = "autopilot_runner_engine_error"
LOG_RUNNER_WAKE_FAILED = "autopilot_runner_wake_failed"

# Telegram notifier cursor over the outbox (oldest first, never skips).
TABLE_NOTIFY_CURSOR = "autopilot_notify_cursor"
NOTIFY_CURSOR_NAME = "telegram"
NOTIFY_CURSOR_NAME_LENGTH = 32
OUTBOX_EVENT_ID_LENGTH = 36

# Topic intake: concurrent POSTs are serialized with an advisory lock.
DIALECT_POSTGRESQL = "postgresql"
ADVISORY_LOCK_PARAM = "key"
ADVISORY_LOCK_SQL = "SELECT pg_advisory_xact_lock(:key)"
INTAKE_LOCK_KEY = 0x41505449  # "APTI": autopilot topic intake
