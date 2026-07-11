"""Constants for the deterministic carousel repair endpoint (AE-0311).

The repair endpoint runs the bounded deterministic repair pipeline over a
carousel's localized slides and writes the fixed copy to both the
``carousel_slides`` projection and the LangGraph checkpoint (the two-commit
contract). These constants name the log/audit events and the workflow-state
keys the repair path reads and writes.
"""

from __future__ import annotations

# Structured-log events (AE-0311 deliverable 4 + drift reconciler).
LOG_EVENT_REPAIR_APPLIED = "carousel_deterministic_repair_applied"
LOG_EVENT_REPAIR_NOOP = "carousel_deterministic_repair_noop"
LOG_EVENT_DRIFT_DETECTED = "carousel_repair_drift_detected"
LOG_EVENT_DRIFT_CONVERGED = "carousel_repair_drift_converged"

# Workflow audit event type + aggregate (shares the existing audit path).
AUDIT_EVENT_REPAIR_APPLIED = "carousel.repair.applied"
AUDIT_AGGREGATE_CAROUSEL = "carousel"

# Repair response statuses.
REPAIR_STATUS_REPAIRED = "repaired"
REPAIR_STATUS_NOOP = "noop"

# Reconciliation-store identifiers reported on partial failure.
REPAIR_STORE_PROJECTION = "projection"
REPAIR_STORE_CHECKPOINT = "checkpoint"

__all__ = [
    "AUDIT_AGGREGATE_CAROUSEL",
    "AUDIT_EVENT_REPAIR_APPLIED",
    "LOG_EVENT_DRIFT_CONVERGED",
    "LOG_EVENT_DRIFT_DETECTED",
    "LOG_EVENT_REPAIR_APPLIED",
    "LOG_EVENT_REPAIR_NOOP",
    "REPAIR_STATUS_NOOP",
    "REPAIR_STATUS_REPAIRED",
    "REPAIR_STORE_CHECKPOINT",
    "REPAIR_STORE_PROJECTION",
]
