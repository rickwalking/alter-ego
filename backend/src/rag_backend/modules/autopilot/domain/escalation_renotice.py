"""Which stuck run the daily scan may notify once more, and how. Pure."""

from __future__ import annotations

from dataclasses import replace

from rag_backend.modules.autopilot.constants import PAYLOAD_REASON, PAYLOAD_STATE
from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.notice_log import NoticeLog
from rag_backend.modules.autopilot.renotice_constants import (
    RENOTICE_KEY,
    RENOTICE_STATES,
    RESOLVED_REASONS,
)


def renotice_due(run: AutopilotRun) -> bool:
    """A stuck run with a carousel, not closed, not re-notified yet."""
    if run.state not in RENOTICE_STATES or not run.carousel_project_id:
        return False
    if run.state_reason in RESOLVED_REASONS:
        return False
    return RENOTICE_KEY not in run.notice_log.statuses


def mark_renoticed(log: NoticeLog) -> NoticeLog:
    """``log`` with the marker that keeps the run to one re-sent notice."""
    return replace(log, statuses=(*log.statuses, RENOTICE_KEY))


def renotice_payload(run: AutopilotRun) -> dict[str, object]:
    """The event payload: the notice shows the run's own reason."""
    return {
        PAYLOAD_STATE: run.state.value,
        PAYLOAD_REASON: run.state_reason or run.state.value,
    }


__all__ = ["mark_renoticed", "renotice_due", "renotice_payload"]
