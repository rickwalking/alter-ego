"""Constants for the carousel generation queue (ADR-0026).

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

DEDUPE_AUTOPILOT = "autopilot:{run_id}"
DEDUPE_RESUME = "resume:{project_id}:{lock_version}"

ENTRYPOINT = "carousel_generation"

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
