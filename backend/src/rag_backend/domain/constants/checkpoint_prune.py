"""Constants of the signed-off carousel checkpoint prune."""

from __future__ import annotations

CHECKPOINTS_TABLE = "checkpoints"
CHECKPOINT_WRITES_TABLE = "checkpoint_writes"
CHECKPOINT_BLOBS_TABLE = "checkpoint_blobs"
CHANNEL_VERSIONS_KEY = "channel_versions"

AUTOPILOT_RUNS_TABLE = "autopilot_runs"

BACKUP_DIR_NAME = "checkpoint-prune"
BACKUP_FILE_NAME = "checkpoint-prune-{stamp}.jsonl"
BACKUP_STAMP_FORMAT = "%Y%m%dT%H%M%SZ"
BACKUP_TABLE_KEY = "table"
BACKUP_ROW_KEY = "row"
PG_RESTORE_BINARY = "pg_restore"
PG_RESTORE_LIST_FLAG = "--list"
PG_RESTORE_TIMEOUT_SECONDS = 120
PG_DUMP_TABLE_DATA = ("TABLE", "DATA")

LOG_PRUNE_CANDIDATES = "checkpoint_prune_candidates"
LOG_PRUNE_DONE = "checkpoint_prune_done"
LOG_PRUNE_REFUSED = "checkpoint_prune_refused"
LOG_PRUNE_RESTORED = "checkpoint_prune_restored"

ERR_NOT_ELIGIBLE = "signed-off threads are no longer eligible: {threads}"
ERR_NO_THREADS = "the sign-off file names no thread"
ERR_NOOP = "signed-off threads had {expected} prunable rows but none was deleted"
ERR_PARTIAL = "deleted {deleted} rows but {expected} were prunable; rolled back"
ERR_BACKUP_MISMATCH = "backup holds {written} rows but {expected} are prunable"
ERR_PG_RESTORE_MISSING = "pg_restore is not installed; cannot verify the --pg-dump file"
ERR_PG_DUMP_UNREADABLE = "pg_restore cannot read the --pg-dump file: {detail}"
ERR_PG_DUMP_TABLES = "the --pg-dump file holds no data for: {tables}"
ERR_DELTA_CHANNEL = "the carousel graph keeps history-dependent state: {channels}"
ERR_BACKUP_LINE = "backup line {line} is not a checkpoint table row"
