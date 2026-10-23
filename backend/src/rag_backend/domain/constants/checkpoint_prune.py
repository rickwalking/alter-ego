"""Constants of the signed-off carousel checkpoint prune."""

from __future__ import annotations

CHECKPOINTS_TABLE = "checkpoints"
CHECKPOINT_WRITES_TABLE = "checkpoint_writes"
CHECKPOINT_BLOBS_TABLE = "checkpoint_blobs"
CHANNEL_VERSIONS_KEY = "channel_versions"

AUTOPILOT_RUNS_TABLE = "autopilot_runs"
AUTOPILOT_SETTLED_STATES = ("published", "rejected", "expired")

LOG_PRUNE_CANDIDATES = "checkpoint_prune_candidates"
LOG_PRUNE_DONE = "checkpoint_prune_done"
LOG_PRUNE_REFUSED = "checkpoint_prune_refused"

ERR_NOT_ELIGIBLE = "signed-off threads are no longer eligible: {threads}"
ERR_NO_THREADS = "the sign-off file names no thread"
ERR_NOOP = "signed-off threads had {expected} prunable rows but none was deleted"
ERR_PARTIAL = "deleted {deleted} rows but {expected} were prunable; rolled back"
ERR_BACKUP_MISMATCH = "backup holds {written} rows but {expected} are prunable"
