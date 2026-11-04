"""Which stuck run the daily scan may notify once more, and how. Pure."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from uuid import UUID

from rag_backend.modules.autopilot.constants import PAYLOAD_REASON, PAYLOAD_STATE
from rag_backend.modules.autopilot.domain.dead_letter import (
    is_dead_letter,
    is_parked_notice,
)
from rag_backend.modules.autopilot.domain.messages import notice_kind, reason_of
from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.notice_log import NoticeLog
from rag_backend.modules.autopilot.domain.status_keyboard import status_keyboard
from rag_backend.modules.autopilot.notify_constants import (
    KIND_ESCALATED,
    KIND_PUBLISH_FAILED,
)
from rag_backend.modules.autopilot.renotice_constants import (
    RENOTICE_KEY,
    RENOTICE_STATES,
    RESOLVED_REASONS,
)


@dataclass(frozen=True, kw_only=True)
class PastNotice:
    """One notice event of a run; ``since_retry`` dates it from the carousel Retry."""

    run_id: UUID
    event_type: str
    payload: Mapping[str, object]
    since_retry: bool


def renotice_due(run: AutopilotRun) -> bool:
    """A stuck run with a carousel, not closed or parked, not re-notified yet."""
    if run.state not in RENOTICE_STATES or not run.carousel_project_id:
        return False
    if run.state_reason in RESOLVED_REASONS or is_dead_letter(run.state_reason):
        return False
    return RENOTICE_KEY not in run.notice_log.statuses


def carried_retry(notice: PastNotice) -> bool:
    """Whether this notice offered the owner a Retry when it was emitted.

    A parked notice and a failed publish offered theirs at any date; any other
    escalation only since the carousel Retry shipped.
    """
    kind = notice_kind(notice.event_type, notice.payload)
    if kind is None:
        return False
    if is_parked_notice(kind, reason_of(notice.payload)):
        return True
    if kind == KIND_ESCALATED:
        return notice.since_retry
    if kind != KIND_PUBLISH_FAILED:
        return False
    return status_keyboard(kind, notice.run_id, notice.payload) is not None


def mark_renoticed(log: NoticeLog) -> NoticeLog:
    """``log`` with the marker that keeps the run to one re-sent notice."""
    return replace(log, statuses=(*log.statuses, RENOTICE_KEY))


def renotice_payload(run: AutopilotRun) -> dict[str, object]:
    """The event payload: the notice shows the run's own reason."""
    return {
        PAYLOAD_STATE: run.state.value,
        PAYLOAD_REASON: run.state_reason or run.state.value,
    }


__all__ = [
    "PastNotice",
    "carried_retry",
    "mark_renoticed",
    "renotice_due",
    "renotice_payload",
]
