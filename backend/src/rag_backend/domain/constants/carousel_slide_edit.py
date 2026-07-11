"""Constants for the completed-project slide-text edit endpoint (AE-0314).

The endpoint lets an owner/assigned reviewer fix a typo or casing issue on a
COMPLETED carousel from the publish page WITHOUT regenerating images: it writes
the edited copy to the ``carousel_slides`` projection (authoritative for
completed) + a fresh severity-aware validation report to the checkpoint (via the
park-preserving ``patch_parked_checkpoint``), stamps a persisted
``needs_republish`` marker in the same transaction, and returns the fresh report.
A server-guaranteed republish (client-triggered for speed, watchdog-swept as the
guarantee) rebuilds the PDF from the edited slides.
"""

from __future__ import annotations

# Structured-log events.
LOG_EVENT_SLIDE_EDITED = "carousel_completed_slide_edited"
LOG_EVENT_REPUBLISH_SWEPT = "carousel_republish_marker_swept"

# Workflow audit event type (shares the existing audit path + carousel aggregate).
AUDIT_EVENT_SLIDE_EDITED = "carousel.slide.edited"

# Slide-edit response status.
SLIDE_EDIT_STATUS_UPDATED = "updated"

# Route-level guard: the edit endpoint is completed-only.
ERR_SLIDE_EDIT_NOT_COMPLETED = "carousel_slide_edit_requires_completed"

# Republish-sweep default: a marked project older than this is republished by
# the watchdog as the server-side guarantee (client triggers it sooner).
REPUBLISH_SWEEP_MIN_AGE_SECONDS = 180

__all__ = [
    "AUDIT_EVENT_SLIDE_EDITED",
    "ERR_SLIDE_EDIT_NOT_COMPLETED",
    "LOG_EVENT_REPUBLISH_SWEPT",
    "LOG_EVENT_SLIDE_EDITED",
    "REPUBLISH_SWEEP_MIN_AGE_SECONDS",
    "SLIDE_EDIT_STATUS_UPDATED",
]
