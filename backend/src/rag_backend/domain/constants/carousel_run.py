"""Constants for carousel run-progress visibility and the stale-run reaper (AE-0315)."""

# Coarse run stages emitted at stage boundaries by the background resume path.
RUN_STAGE_GENERATING = "generating"
RUN_STAGE_VALIDATING = "validating"
RUN_STAGE_PERSISTING = "persisting"

RUN_STAGES = (
    RUN_STAGE_GENERATING,
    RUN_STAGE_VALIDATING,
    RUN_STAGE_PERSISTING,
)

# SSE lifecycle event names on the existing workflow stream.
SSE_EVENT_RUN_STARTED = "run.started"
SSE_EVENT_RUN_STAGE_CHANGED = "run.stage_changed"
SSE_EVENT_RUN_FINISHED = "run.finished"

# run.finished reasons.
RUN_FINISHED_REASON_COMPLETED = "completed"
RUN_FINISHED_REASON_FAILED = "failed"
RUN_FINISHED_REASON_STALE = "stale"

# SSE payload field names for run lifecycle events.
SSE_PAYLOAD_FIELD_RUN_STARTED_AT = "run_started_at"
SSE_PAYLOAD_FIELD_RUN_STAGE = "run_stage"
SSE_PAYLOAD_FIELD_RUN_REASON = "reason"

# Structured log event names.
LOG_EVENT_RUN_OVERDUE = "run_overdue"
LOG_EVENT_RUN_REAPED = "carousel_run_reaped"
LOG_EVENT_RUN_NULL_HEARTBEAT = "carousel_run_null_heartbeat_alert"
LOG_EVENT_RUN_HEARTBEAT_FAILED = "carousel_run_heartbeat_failed"
LOG_EVENT_RUN_FENCED = "carousel_run_fenced"

# Reaper defaults (overridable via Settings).
DEFAULT_RUN_HEARTBEAT_INTERVAL_SECONDS = 60
DEFAULT_RUN_HEARTBEAT_STALE_SECONDS = 180
DEFAULT_RUN_REAP_CONSECUTIVE_OBSERVATIONS = 3
DEFAULT_RUN_OVERDUE_MINUTES = 60

# Error message raised by the epoch fence (client-safe; carries no internals).
ERR_STALE_RUN_EPOCH = "carousel_run_epoch_stale"

__all__ = [
    "DEFAULT_RUN_HEARTBEAT_INTERVAL_SECONDS",
    "DEFAULT_RUN_HEARTBEAT_STALE_SECONDS",
    "DEFAULT_RUN_OVERDUE_MINUTES",
    "DEFAULT_RUN_REAP_CONSECUTIVE_OBSERVATIONS",
    "ERR_STALE_RUN_EPOCH",
    "LOG_EVENT_RUN_FENCED",
    "LOG_EVENT_RUN_HEARTBEAT_FAILED",
    "LOG_EVENT_RUN_NULL_HEARTBEAT",
    "LOG_EVENT_RUN_OVERDUE",
    "LOG_EVENT_RUN_REAPED",
    "RUN_FINISHED_REASON_COMPLETED",
    "RUN_FINISHED_REASON_FAILED",
    "RUN_FINISHED_REASON_STALE",
    "RUN_STAGES",
    "RUN_STAGE_GENERATING",
    "RUN_STAGE_PERSISTING",
    "RUN_STAGE_VALIDATING",
    "SSE_EVENT_RUN_FINISHED",
    "SSE_EVENT_RUN_STAGE_CHANGED",
    "SSE_EVENT_RUN_STARTED",
    "SSE_PAYLOAD_FIELD_RUN_REASON",
    "SSE_PAYLOAD_FIELD_RUN_STAGE",
    "SSE_PAYLOAD_FIELD_RUN_STARTED_AT",
]
