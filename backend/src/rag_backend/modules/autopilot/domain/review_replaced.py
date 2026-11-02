"""A tap on a review message a newer review replaced. No I/O.

Telegram buttons carry only the run id, so an old review message would act on
whatever the carousel shows now. Once a newer review was sent (a website cover
re-rendered slide 1, a rework, a fix), the approve, publish and schedule
buttons of an older review message change nothing.
"""

from __future__ import annotations

from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.notice_log import reminder_revision


def is_replaced_review(run: AutopilotRun | None, message_id: int | None) -> bool:
    """True when ``message_id`` is the keyboard of an older review of ``run``."""
    if run is None or message_id is None:
        return False
    log = run.notice_log
    tapped = next(
        (review for review in log.reviews if review.keyboard_id == message_id), None
    )
    if tapped is None:
        return False
    return tapped.revision < reminder_revision(log)


__all__ = ["is_replaced_review"]
