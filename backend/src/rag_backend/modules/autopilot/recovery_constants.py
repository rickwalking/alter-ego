"""Run-recovery and manual-publish constants (AE-0348 QA round 1).

Kept beside ``constants.py`` so neither file exceeds the 400-line limit.
"""

from __future__ import annotations

import math

from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN,
    GRAPH_PUBLISH_WORST_CASE_SECONDS,
)

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
# QA r2 R1: escalations are closed instead of blocking the scan forever. The
# window matches the owner-review expiry and the carousel stuck auto-reject.
REASON_ESCALATION_EXPIRED = "escalation_expired"
REASON_CAROUSEL_REJECTED = "carousel_rejected"

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
# A claim is taken over only once its holder cannot still be talking to
# Graph: the slowest possible publish plus a margin (QA r2 R4a).
CLAIM_STALE_MARGIN_MINUTES = 5
SECONDS_PER_MINUTE = 60
MANUAL_CLAIM_STALE_MINUTES = (
    math.ceil(GRAPH_PUBLISH_WORST_CASE_SECONDS / SECONDS_PER_MINUTE)
    + CLAIM_STALE_MARGIN_MINUTES
)
# Approve sets ``publishing`` before the release makes the carousel public;
# the worker waits this long before failing a not-yet-public run (QA r2 R4c).
RELEASE_GRACE_SECONDS = 300
REASON_RELEASE_PENDING = "carousel_release_pending"
# QA r3 Q2: a dead worker's container holds the run. Its status is read once
# per tick; the owner is told once when the hold passes this many minutes.
PUBLISH_HELD_NOTICE_MINUTES = 30
REASON_PUBLISH_HELD = "publish_held_by_container"
NOTICE_PUBLISH_HELD = "publish_held"
ERR_AUTOPILOT_RUN_ACTIVE = "autopilot_run_not_publishing"
ERR_PUBLISH_IN_PROGRESS = "instagram_publish_in_progress"
# QA r2 R3: the post may already be live. Retry would open a new container
# and could post the carousel twice, so it is never offered or accepted.
NO_RETRY_REASONS = frozenset({ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN})

# Review reopened without regeneration: the keyboard is sent again.
REASON_REVIEW_REOPENED = "review_reopened"
LOG_RUNNER_ENGINE_ERROR = "autopilot_runner_engine_error"
LOG_RUNNER_WAKE_FAILED = "autopilot_runner_wake_failed"

# Telegram notifier cursor over the outbox (oldest first, never skips).
TABLE_NOTIFY_CURSOR = "autopilot_notify_cursor"
NOTIFY_CURSOR_NAME = "telegram"
NOTIFY_CURSOR_NAME_LENGTH = 32
OUTBOX_EVENT_ID_LENGTH = 36
# ``created_at`` is the transaction start, so a long transaction can commit an
# event behind the cursor. Each scan re-reads this window behind it (QA r2 R5).
NOTIFY_RESCAN_WINDOW_MINUTES = 10

# Topic intake: concurrent POSTs are serialized with an advisory lock.
DIALECT_POSTGRESQL = "postgresql"
ADVISORY_LOCK_PARAM = "key"
ADVISORY_LOCK_SQL = "SELECT pg_advisory_xact_lock(:key)"
INTAKE_LOCK_KEY = 0x41505449  # "APTI": autopilot topic intake
