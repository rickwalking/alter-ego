"""Constants for stuck-workflow auto-reject.

CLAUDE.md mandates "Auto-reject after timeout; never leave workflows stuck."
These constants name the terminal transition and the audit/event payload fields
applied when a workflow exceeds the configured timeout.
"""

AUTO_REJECT_CAROUSEL_STATUS = "failed"

AUTO_REJECT_ERROR_MESSAGE = (
    "Auto-rejected: workflow exceeded the stuck-workflow timeout "
    "(never-stuck policy, AE-0210)."
)

AUTO_REJECT_LOG_EVENT = "workflow_auto_rejected"

AUTO_REJECT_PAYLOAD_PREVIOUS_PHASE = "previous_phase"
AUTO_REJECT_PAYLOAD_PREVIOUS_PHASE_STATUS = "previous_phase_status"
AUTO_REJECT_PAYLOAD_NEW_PHASE_STATUS = "phase_status"
AUTO_REJECT_PAYLOAD_REASON = "reason"
AUTO_REJECT_PAYLOAD_TIMEOUT_HOURS = "timeout_hours"

AUTO_REJECT_EVENT_SOURCE = "workflow_timeout"

__all__ = [
    "AUTO_REJECT_CAROUSEL_STATUS",
    "AUTO_REJECT_ERROR_MESSAGE",
    "AUTO_REJECT_EVENT_SOURCE",
    "AUTO_REJECT_LOG_EVENT",
    "AUTO_REJECT_PAYLOAD_NEW_PHASE_STATUS",
    "AUTO_REJECT_PAYLOAD_PREVIOUS_PHASE",
    "AUTO_REJECT_PAYLOAD_PREVIOUS_PHASE_STATUS",
    "AUTO_REJECT_PAYLOAD_REASON",
    "AUTO_REJECT_PAYLOAD_TIMEOUT_HOURS",
]
