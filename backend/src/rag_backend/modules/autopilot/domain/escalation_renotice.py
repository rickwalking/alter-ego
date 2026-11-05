"""Which stuck run the daily scan may notify once more, and how. Pure."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.constants import PAYLOAD_REASON, PAYLOAD_STATE
from rag_backend.modules.autopilot.domain.dead_letter import (
    is_dead_letter,
    is_parked_notice,
)
from rag_backend.modules.autopilot.domain.messages import notice_kind, reason_of
from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.notice_log import NoticeLog, attempt_count
from rag_backend.modules.autopilot.domain.status_keyboard import status_keyboard
from rag_backend.modules.autopilot.notify_constants import (
    ATTEMPT_STATUS_PREFIX,
    KIND_ESCALATED,
    KIND_PUBLISH_FAILED,
    NOTIFY_MAX_ATTEMPTS,
)
from rag_backend.modules.autopilot.renotice_constants import (
    RENOTICE_KEY,
    RENOTICE_KEY_FORMAT,
    RENOTICE_SENDING_KEY,
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


class RenoticeClaims(Protocol):
    """The durable claim on one notice's send."""

    async def take(self, run_id: UUID, event_id: str) -> bool:
        """Claim the send and commit; False when it is claimed or delivered."""
        ...

    async def release(self, run_id: UUID, event_id: str) -> None:
        """Drop the claim: the send certainly did not happen. The caller commits."""
        ...


def renotice_due(run: AutopilotRun) -> bool:
    """A stuck run with a carousel, not closed or parked, whose notices all failed."""
    if run.state not in RENOTICE_STATES or not run.carousel_project_id:
        return False
    if run.state_reason in RESOLVED_REASONS or is_dead_letter(run.state_reason):
        return False
    log = run.notice_log
    return all(_given_up(log, event_id) for event_id in _queued(log))


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


def mark_renoticed(log: NoticeLog, event_id: str) -> NoticeLog:
    """``log`` with the marker of the notice queued as ``event_id``."""
    marker = RENOTICE_KEY_FORMAT.format(key=RENOTICE_KEY, event_id=event_id)
    return replace(log, statuses=(*log.statuses, marker))


def send_claimed(log: NoticeLog, event_id: str) -> bool:
    """True when a send of ``event_id`` started and may have been delivered."""
    return _claim(event_id) in log.statuses


def claim_send(log: NoticeLog, event_id: str) -> NoticeLog:
    """``log`` with the claim taken before ``event_id`` is sent."""
    return replace(log, statuses=(*log.statuses, _claim(event_id)))


def release_send(log: NoticeLog, event_id: str) -> NoticeLog:
    """``log`` without the claim: that send certainly did not happen."""
    claim = _claim(event_id)
    return replace(log, statuses=tuple(item for item in log.statuses if item != claim))


def renotice_payload(run: AutopilotRun) -> dict[str, object]:
    """The event payload: the notice shows the run's own reason."""
    return {
        PAYLOAD_STATE: run.state.value,
        PAYLOAD_REASON: run.state_reason or run.state.value,
    }


def _claim(event_id: str) -> str:
    return RENOTICE_KEY_FORMAT.format(key=RENOTICE_SENDING_KEY, event_id=event_id)


def _queued(log: NoticeLog) -> list[str]:
    prefix = RENOTICE_KEY_FORMAT.format(key=RENOTICE_KEY, event_id="")
    return [
        status.removeprefix(prefix)
        for status in log.statuses
        if status.startswith(prefix)
    ]


def _given_up(log: NoticeLog, event_id: str) -> bool:
    """Certainly undelivered: not recorded, no send in doubt, no attempt left."""
    if event_id in log.statuses or send_claimed(log, event_id):
        return False
    key = f"{ATTEMPT_STATUS_PREFIX}{event_id}"
    return attempt_count(log, key) >= NOTIFY_MAX_ATTEMPTS


__all__ = [
    "PastNotice",
    "RenoticeClaims",
    "carried_retry",
    "claim_send",
    "mark_renoticed",
    "release_send",
    "renotice_due",
    "renotice_payload",
    "send_claimed",
]
