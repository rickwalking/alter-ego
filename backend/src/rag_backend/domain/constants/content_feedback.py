"""Constants for the reviewer feedback-note lifecycle (AE-0405).

A revision note is active until the regeneration that uses it runs; it then
moves to a per-phase history kept for the audit and the persona feedback loop.
"""

# Workflow state fields. ``phase_feedback`` (STATE_FIELD_PHASE_FEEDBACK) keeps
# the ACTIVE note texts (API shape unchanged); these two carry the metadata.
STATE_FIELD_FEEDBACK_NOTES = "phase_feedback_notes"
STATE_FIELD_FEEDBACK_HISTORY = "phase_feedback_history"
# True while the graph is parked at the content review and the artifacts that
# review shows were written to the checkpoint: the node replay on resume reuses
# them instead of running the content ensure (and its LLM calls) again.
STATE_FIELD_CONTENT_ARTIFACTS_PARKED = "content_artifacts_parked"
# Content interrupt payload key carrying that pass's artifact updates, which
# the engine writes to the checkpoint once the graph parks.
PAYLOAD_KEY_PARKED_ARTIFACTS = "parked_artifact_updates"

# Structured-feedback key naming who wrote the note (autopilot vs human).
STRUCTURED_FEEDBACK_SOURCE_KEY = "feedback_source"
FEEDBACK_SOURCE_HUMAN = "human"
FEEDBACK_SOURCE_AUTOPILOT = "autopilot"

# Note entry fields.
FEEDBACK_ENTRY_NOTE = "note"
FEEDBACK_ENTRY_SOURCE = "source"
FEEDBACK_ENTRY_ADDED_AT = "added_at"
FEEDBACK_ENTRY_STATUS = "status"
FEEDBACK_ENTRY_SETTLED_AT = "settled_at"

# History statuses: used by a regeneration, dropped (autopilot note whose gate
# passed without it), migrated (legacy untagged note that predates the last
# regeneration).
FEEDBACK_STATUS_APPLIED = "applied"
FEEDBACK_STATUS_DROPPED = "dropped"
FEEDBACK_STATUS_MIGRATED = "migrated"

# structlog events.
LOG_FEEDBACK_APPLIED = "content_feedback_applied"
LOG_FEEDBACK_SETTLED = "content_feedback_settled"
LOG_CONTENT_REPLAY_REUSED = "content_artifacts_replay_reused"
LOG_CONTENT_ARTIFACTS_PARKED = "content_artifacts_parked"
# AE-0413: a manual-fixes revise keeps the edited copy (no content ensure).
LOG_CONTENT_MANUAL_FIXES_KEPT = "content_manual_fixes_kept"

__all__ = [
    "FEEDBACK_ENTRY_ADDED_AT",
    "FEEDBACK_ENTRY_NOTE",
    "FEEDBACK_ENTRY_SETTLED_AT",
    "FEEDBACK_ENTRY_SOURCE",
    "FEEDBACK_ENTRY_STATUS",
    "FEEDBACK_SOURCE_AUTOPILOT",
    "FEEDBACK_SOURCE_HUMAN",
    "FEEDBACK_STATUS_APPLIED",
    "FEEDBACK_STATUS_DROPPED",
    "FEEDBACK_STATUS_MIGRATED",
    "LOG_CONTENT_ARTIFACTS_PARKED",
    "LOG_CONTENT_MANUAL_FIXES_KEPT",
    "LOG_CONTENT_REPLAY_REUSED",
    "LOG_FEEDBACK_APPLIED",
    "LOG_FEEDBACK_SETTLED",
    "PAYLOAD_KEY_PARKED_ARTIFACTS",
    "STATE_FIELD_CONTENT_ARTIFACTS_PARKED",
    "STATE_FIELD_FEEDBACK_HISTORY",
    "STATE_FIELD_FEEDBACK_NOTES",
    "STRUCTURED_FEEDBACK_SOURCE_KEY",
]
