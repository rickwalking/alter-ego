"""Run-recovery and manual-publish constants (QA round 1).

Kept beside ``constants.py`` so neither file exceeds the 400-line limit.

- Engine errors the runner did not classify end the run with a reason instead of rolling
  back the whole worker tick on every retry.
- Design revises at most once (architecture §6); other gates twice.
- Owner reviews expire after 72 hours in ``awaiting_owner``; escalations close after the
  same window instead of blocking the scan forever, matching the carousel stuck auto-
  reject.
- Owner rework is queued by the webhook and applied by the runner.
- A publish claim is taken over only once its holder cannot still be talking to Graph:
  the slowest possible publish plus a margin. The Story runs under the same claim, up to
  ``STORY_MAX_ATTEMPTS`` times.
- Approve sets ``publishing`` before the release makes the carousel public, so the
  worker waits before failing a not-yet-public run.
- A dead worker's Instagram container holds the run; its status is read once per tick
  and the owner is told once when the hold passes the threshold.
- When the post may already be live, Retry is never offered or accepted: a new container
  could post the carousel twice.
- The Telegram notifier reads the outbox oldest first and never skips. ``created_at`` is
  the transaction start, so a long transaction can commit an event behind the cursor;
  each scan re-reads a window behind it.
- Concurrent topic-intake POSTs are serialized with an advisory lock keyed by “APTI”
  (autopilot topic intake).
"""

from __future__ import annotations

import math

from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN,
    GRAPH_PUBLISH_WORST_CASE_SECONDS,
    GRAPH_STORY_WORST_CASE_SECONDS,
)
from rag_backend.modules.autopilot.story_constants import STORY_MAX_ATTEMPTS

REASON_ENGINE_ERROR = "engine_error"
REASON_ENGINE_ERROR_FORMAT = "{prefix}:{kind}:{detail}"
ENGINE_ERROR_DETAIL_MAX_CHARS = 160

MAX_REVISES_DESIGN = 1

OWNER_REVIEW_EXPIRY_HOURS = 72
REASON_OWNER_EXPIRED = "owner_review_expired"
EXPIRY_SCAN_LIMIT = 20

REASON_OWNER_FIXED = "owner_fixed_in_web_ui"
ESCALATED_SCAN_LIMIT = 5
REASON_ESCALATION_EXPIRED = "escalation_expired"
REASON_CAROUSEL_REJECTED = "carousel_rejected"

REASON_REWORK_QUEUED = "owner_rework_queued"
REASON_REWORK_RETRY = "owner_rework_not_applied"
REASON_APPROVE_REFUSED = "owner_approve_refused"

TABLE_MANUAL_PUBLISHES = "instagram_manual_publishes"
FK_MANUAL_PUBLISH_PROJECT = "fk_instagram_manual_publishes_carousel_project"
ON_DELETE_CASCADE = "CASCADE"
REWORK_PHASE_LENGTH = 32
MANUAL_STATE_PUBLISHING = "publishing"
MANUAL_STATE_PUBLISHED = "published"
MANUAL_STATE_FAILED = "failed"
CLAIM_STALE_MARGIN_MINUTES = 5
SECONDS_PER_MINUTE = 60
CLAIM_HELD_WORST_CASE_SECONDS = (
    GRAPH_PUBLISH_WORST_CASE_SECONDS
    + STORY_MAX_ATTEMPTS * GRAPH_STORY_WORST_CASE_SECONDS
)
MANUAL_CLAIM_STALE_MINUTES = (
    math.ceil(CLAIM_HELD_WORST_CASE_SECONDS / SECONDS_PER_MINUTE)
    + CLAIM_STALE_MARGIN_MINUTES
)
RELEASE_GRACE_SECONDS = 300
REASON_RELEASE_PENDING = "carousel_release_pending"
PUBLISH_HELD_NOTICE_MINUTES = 30
REASON_PUBLISH_HELD = "publish_held_by_container"
NOTICE_PUBLISH_HELD = "publish_held"
ERR_AUTOPILOT_RUN_ACTIVE = "autopilot_run_not_publishing"
ERR_PUBLISH_IN_PROGRESS = "instagram_publish_in_progress"
NO_RETRY_REASONS = frozenset({ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN})

REASON_REVIEW_REOPENED = "review_reopened"
LOG_RUNNER_ENGINE_ERROR = "autopilot_runner_engine_error"
LOG_RUNNER_WAKE_FAILED = "autopilot_runner_wake_failed"

TABLE_NOTIFY_CURSOR = "autopilot_notify_cursor"
NOTIFY_CURSOR_NAME = "telegram"
NOTIFY_CURSOR_NAME_LENGTH = 32
OUTBOX_EVENT_ID_LENGTH = 36
NOTIFY_RESCAN_WINDOW_MINUTES = 10

DIALECT_POSTGRESQL = "postgresql"
ADVISORY_LOCK_PARAM = "key"
ADVISORY_LOCK_SQL = "SELECT pg_advisory_xact_lock(:key)"
INTAKE_LOCK_KEY = 0x41505449
