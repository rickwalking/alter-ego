"""Constants for the completed-project slide-text edit endpoint.

The endpoint lets an owner/assigned reviewer fix a typo or casing issue on a
COMPLETED carousel from the publish page WITHOUT regenerating images: it writes
the edited copy to the ``carousel_slides`` projection (authoritative for
completed) + a fresh severity-aware validation report to the checkpoint (via the
park-preserving ``patch_parked_checkpoint``), stamps a persisted
``needs_republish`` marker in the same transaction, and returns the fresh report.
A server-guaranteed republish (client-triggered for speed, watchdog-swept as the
guarantee) rebuilds the PDF from the edited slides.

A structured-item violation field path looks like ``summary_points[0].body`` (list key,
item index, sub-field); plain ``heading`` and ``body`` do not match. The watchdog
republishes a marked project older than ``REPUBLISH_SWEEP_MIN_AGE_SECONDS`` as the
server-side guarantee; the client triggers it sooner.
"""

from __future__ import annotations

LOG_EVENT_SLIDE_EDITED = "carousel_completed_slide_edited"
LOG_EVENT_REPUBLISH_SWEPT = "carousel_republish_marker_swept"

AUDIT_EVENT_SLIDE_EDITED = "carousel.slide.edited"

SLIDE_EDIT_STATUS_UPDATED = "updated"

ERR_SLIDE_EDIT_NOT_COMPLETED = "carousel_slide_edit_requires_completed"

STRUCTURED_ITEM_FIELD_PATTERN = (
    r"^(?P<list>[a-z_]+)\[(?P<index>\d+)\]\.(?P<field>[a-z_]+)$"
)

REPUBLISH_SWEEP_MIN_AGE_SECONDS = 180

__all__ = [
    "AUDIT_EVENT_SLIDE_EDITED",
    "ERR_SLIDE_EDIT_NOT_COMPLETED",
    "LOG_EVENT_REPUBLISH_SWEPT",
    "LOG_EVENT_SLIDE_EDITED",
    "REPUBLISH_SWEEP_MIN_AGE_SECONDS",
    "SLIDE_EDIT_STATUS_UPDATED",
    "STRUCTURED_ITEM_FIELD_PATTERN",
]
