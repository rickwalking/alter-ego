"""Constants for the carousel generation queue.

Budgets and delays come from the generation queue plan: at most 3 unfinished attempts
per (run, phase) and 10 per run, retries from 30 s doubling to 30 min with ±20 %
jitter, a 300 s heartbeat timeout, and a dispatcher pass every 10 s.
"""

MODULE_NAME = "generation_queue"

TABLE_GENERATION_RUNS = "generation_runs"
INDEX_STATUS_CREATED = "ix_generation_runs_status_created_at"
INDEX_ACTIVE_DEDUPE = "uq_generation_runs_active_dedupe_key"
INDEX_PROJECT = "ix_generation_runs_carousel_project_id"
INDEX_AUTOPILOT_RUN = "ix_generation_runs_autopilot_run_id"

KIND_LENGTH = 32
STATUS_LENGTH = 16
DEDUPE_KEY_LENGTH = 160
PHASE_LENGTH = 64
ERROR_CODE_LENGTH = 64
ERROR_MESSAGE_MAX_CHARS = 2000

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_RETRY_WAIT = "retry_wait"
STATUS_SUCCEEDED = "succeeded"
STATUS_DEAD_LETTER = "dead_letter"
STATUS_CANCELLED = "cancelled"
ACTIVE_STATUSES = (STATUS_QUEUED, STATUS_RUNNING, STATUS_RETRY_WAIT)

KIND_AUTOPILOT_DRIVE = "autopilot_drive"
KIND_WORKFLOW_RESUME = "workflow_resume"
DRIVEN_AUTOPILOT_STATES = ("queued", "generating", "reworking")
AUTOPILOT_OWNER_WAIT_STATES = ("awaiting_owner", "awaiting_thesis")

DEDUPE_AUTOPILOT = "autopilot:{run_id}"
DEDUPE_RESUME = "resume:{project_id}:{lock_version}"
DEDUPE_ADOPT = "adopt:{project_id}"
ACTION_ADOPT = "adopt"
ADOPT_REVIEWER = "generation-queue"
TABLE_AUTOPILOT_RUNS = "autopilot_runs"
COLUMN_CAROUSEL_PROJECT_ID = "carousel_project_id"

ENTRYPOINT = "carousel_generation"
MAINTENANCE_ENTRYPOINT = "generation_maintenance"
MAINTENANCE_FULL = "full"
MAINTENANCE_DISPATCH_PREFIX = "dispatch:"
MAINTENANCE_ADVISORY_KEY = 5520552
ORDINARY_PRIORITY = 0

MAX_PHASE_ATTEMPTS = 3
MAX_RUN_ATTEMPTS = 10
PHASE_START = "start"

RETRY_INITIAL_SECONDS = 30
RETRY_MULTIPLIER = 2
RETRY_MAX_SECONDS = 1800
RETRY_JITTER = 0.2

WAIT_DELAY_SECONDS = 60
RESTART_DELAY_SECONDS = 0
LOCK_WAIT_SECONDS = 60
LOCK_POLL_SECONDS = 2.0
LOCK_BUSY_DELAY_SECONDS = 120
LOCK_WATCH_SECONDS = 30.0
MAX_STEPS_PER_JOB = 40

HEARTBEAT_TIMEOUT_SECONDS = 300
DISPATCH_INTERVAL_SECONDS = 10.0
DISPATCH_BATCH = 20
ORPHAN_JOB_GRACE_SECONDS = 600

PROGRESS_CHANNEL = "carousel_progress"
MAX_NOTIFY_BYTES = 7900

ERROR_TRANSIENT = "transient"
ERROR_PERMANENT = "permanent"
ERROR_PHASE_BUDGET = "phase_budget_exhausted"
ERROR_RUN_BUDGET = "run_budget_exhausted"
ERROR_HELD_JOB = "held_by_queue"
ERROR_UNKNOWN_KIND = "unknown_kind"
ERROR_BAD_PAYLOAD = "bad_payload"
ERR_PAYLOAD_FIELD = "invalid payload field: {field}"

LOG_STAGED = "generation_run_staged"
LOG_DISPATCHED = "generation_run_dispatched"
LOG_STARTED = "generation_run_started"
LOG_SUCCEEDED = "generation_run_succeeded"
LOG_RETRY = "generation_run_retry"
LOG_DEAD_LETTER = "generation_run_dead_letter"
LOG_LOCK_BUSY = "generation_run_lock_busy"
LOG_LOCK_LOST = "generation_run_lock_lost"
LOG_ORPHAN_REAPED = "generation_run_orphan_reaped"
LOG_ORPHAN_ADOPTED = "generation_run_orphan_adopted"
LOG_DISPATCH_FAILED = "generation_dispatch_failed"
LOG_RELAY_FAILED = "generation_progress_relay_failed"
LOG_WORKER_STARTED = "generation_worker_started"
LOG_WORKER_STOPPED = "generation_worker_stopped"
LOG_PERIODIC_FAILED = "generation_worker_periodic_failed"

WORKER_APPLICATION_NAME = "generation-worker"
WORKER_MISSING_ALERT_SECONDS = 600
OLDEST_QUEUED_ALERT_SECONDS = 6 * 3600
MONITOR_INTERVAL_SECONDS = 60.0
ALERT_WORKER_MISSING = (
    "Fila de geração: o worker não está conectado há {minutes} min. "
    "Carrosséis aprovados ficam esperando até ele voltar."
)
ALERT_QUEUE_STALLED = (
    "Fila de geração: o tema mais antigo espera há {hours} h ({queued} na fila)."
)
LOG_QUEUE_ALERT = "generation_queue_alert"

SCAN_ENTRYPOINT = "daily_recovery_scan"
SCAN_CRON_UTC = "0 7 * * *"
SCAN_RECOVERY_DAYS = 7
SCAN_STALE_HOURS = 72
SCAN_PURGE_DAYS = 30
SCAN_BATCH = 50
PAYLOAD_RECOVERY_ATTEMPT = "recovery_attempt"
PAYLOAD_MANUAL_ORIGIN = "manual_origin"
MANUAL_ORIGIN_REPROCESS = "carousel_reprocess"
PAYLOAD_MANUAL_REQUEST_ID = "manual_request_id"
PAYLOAD_MANUAL_ACTOR_ID = "manual_actor_id"
PAYLOAD_MANUAL_STUCK_KIND = "manual_stuck_kind"
PAYLOAD_MANUAL_REQUESTED_AT = "manual_requested_at"
PAYLOAD_MANUAL_PRIORITY = "manual_priority"
PAYLOAD_MANUAL_REPLACES_RUN_ID = "replaces_generation_run_id"
PAYLOAD_MANUAL_ACCELERATE_JOB_ID = "manual_accelerate_job_id"
PAYLOAD_MANUAL_CANCEL_JOB_ID = "manual_cancel_job_id"
PAYLOAD_MANUAL_CANCEL_ATTEMPT_ID = "manual_cancel_attempt_id"
MANUAL_REPROCESS_PRIORITY = 1
AUDIT_CAROUSEL_REPROCESS = "carousel.reprocess.requested"
AGGREGATE_CAROUSEL = "carousel"
AGGREGATE_GENERATION_RUN = "generation_run"
RECOVERABLE_ERROR_CODES = (
    ERROR_TRANSIENT,
    ERROR_PHASE_BUDGET,
    ERROR_RUN_BUDGET,
    ERROR_HELD_JOB,
)
SUMMARY_SCAN = (
    "🌅 Varredura diária da fila: {recovered} recolocado(s) na fila, "
    f"{{dead}} parado(s) nos últimos {SCAN_RECOVERY_DAYS} dias, "
    "{queued} na fila agora."
)
SUMMARY_INTERACTIVE = "Projetos do painel parados (retome pelo editor): {titles}"
SUMMARY_FAILURES = "Falhas ao recuperar: {items}"
SUMMARY_FAILURE_ITEM = "{run_id}: {reason}"
SUMMARY_FAILURE_OVERFLOW = "… e mais {count}"
SUMMARY_TITLE_MAX_CHARS = 80
SUMMARY_TITLES_MAX = 10
LOG_SCAN_DONE = "generation_daily_scan_done"
LOG_SCAN_FAILED = "generation_daily_scan_failed"
LOG_SCAN_ITEM_FAILED = "generation_daily_recovery_item_failed"
