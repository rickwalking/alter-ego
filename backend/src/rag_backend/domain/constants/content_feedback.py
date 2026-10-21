"""Constants for the reviewer feedback-note lifecycle.

A revision note is active until the regeneration that uses it runs; it then
moves to a per-phase history kept for the audit and the persona feedback loop.

``phase_feedback`` keeps the active note texts (API shape unchanged) and
``phase_feedback_notes`` carries their metadata. ``content_artifacts_parked`` is true
while the graph is parked at the content review with that review's artifacts in the
checkpoint, so the node replay on resume reuses them instead of re-running the content
ensure and its LLM calls; the content interrupt payload carries those artifact updates
for the engine to write once the graph parks. History statuses: applied (used by a
regeneration), dropped (an autopilot note whose gate passed without it), migrated (a
legacy untagged note older than the last regeneration) and unchanged (used, but the
visible copy did not change). A manual-fixes revise keeps the edited copy without a
content ensure.
"""

STATE_FIELD_FEEDBACK_NOTES = "phase_feedback_notes"
STATE_FIELD_FEEDBACK_HISTORY = "phase_feedback_history"
STATE_FIELD_CONTENT_ARTIFACTS_PARKED = "content_artifacts_parked"
PAYLOAD_KEY_PARKED_ARTIFACTS = "parked_artifact_updates"

STRUCTURED_FEEDBACK_SOURCE_KEY = "feedback_source"
FEEDBACK_SOURCE_HUMAN = "human"
FEEDBACK_SOURCE_AUTOPILOT = "autopilot"

FEEDBACK_ENTRY_NOTE = "note"
FEEDBACK_ENTRY_SOURCE = "source"
FEEDBACK_ENTRY_ADDED_AT = "added_at"
FEEDBACK_ENTRY_STATUS = "status"
FEEDBACK_ENTRY_SETTLED_AT = "settled_at"

FEEDBACK_STATUS_APPLIED = "applied"
FEEDBACK_STATUS_DROPPED = "dropped"
FEEDBACK_STATUS_MIGRATED = "migrated"
FEEDBACK_STATUS_UNCHANGED = "unchanged"

LOG_FEEDBACK_APPLIED = "content_feedback_applied"
LOG_FEEDBACK_SETTLED = "content_feedback_settled"
LOG_CONTENT_REPLAY_REUSED = "content_artifacts_replay_reused"
LOG_CONTENT_ARTIFACTS_PARKED = "content_artifacts_parked"
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
    "FEEDBACK_STATUS_UNCHANGED",
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
