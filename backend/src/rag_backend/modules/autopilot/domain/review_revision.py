"""Which review revision a Telegram tap answers. No I/O.

Telegram buttons carry only the run id, so the message the owner tapped is
what ties the tap to the render it showed. A review records its keyboard
message per revision (the lock version it was sent at), and so does every
reminder. Approving, publishing or scheduling is allowed only for the
revision of the tapped message (see ``FinalReviewApproval``); an unknown
message (none of the run's review or reminder keyboards) answers nothing.
"""

from __future__ import annotations

from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.notice_log import reminder_revision


def tapped_revision(run: AutopilotRun | None, message_id: int | None) -> int | None:
    """The revision the tapped review or reminder message was sent for, else None."""
    if run is None or message_id is None:
        return None
    log = run.notice_log
    for review in log.reviews:
        if review.keyboard_id == message_id:
            return review.revision
    for reminder in log.reminder_messages:
        if reminder.message_id == message_id:
            return reminder.revision
    return None


def latest_revision(run: AutopilotRun | None) -> int | None:
    """The newest review revision sent to the owner (a typed time answers it)."""
    if run is None:
        return None
    revision = reminder_revision(run.notice_log)
    return revision or None


__all__ = ["latest_revision", "tapped_revision"]
