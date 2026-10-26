"""Map autopilot state outbox events to Telegram notice kinds."""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.modules.autopilot.constants import PAYLOAD_REASON, PAYLOAD_STATE
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.notify_constants import (
    KIND_ESCALATED,
    KIND_ESCALATION_CLOSED,
    KIND_EXPIRED,
    KIND_FAILED,
    KIND_REVIEW_REOPENED,
)
from rag_backend.modules.autopilot.queue_constants import REASON_OWNER_CANCELLED
from rag_backend.modules.autopilot.recovery_constants import (
    REASON_CAROUSEL_REJECTED,
    REASON_ESCALATION_EXPIRED,
    REASON_REVIEW_REOPENED,
    REASON_REWORK_RETRY,
)

_STATE_KINDS: dict[str, str] = {
    AutopilotRunState.ESCALATED.value: KIND_ESCALATED,
    AutopilotRunState.FAILED.value: KIND_FAILED,
    AutopilotRunState.EXPIRED.value: KIND_EXPIRED,
}
_REOPEN_REASONS = frozenset({REASON_REWORK_RETRY, REASON_REVIEW_REOPENED})
_CLOSE_REASONS = frozenset({REASON_ESCALATION_EXPIRED, REASON_CAROUSEL_REJECTED})


def state_kind(payload: Mapping[str, object]) -> str | None:
    """Ignore only owner-cancel failure notices and retain every genuine failure."""
    state = payload.get(PAYLOAD_STATE)
    if state == AutopilotRunState.FAILED.value and _owner_cancelled(payload):
        return None
    if state == AutopilotRunState.AWAITING_OWNER.value:
        return _reopened_kind(payload)
    if state == AutopilotRunState.REJECTED.value:
        return _closed_kind(payload)
    return _STATE_KINDS.get(str(state))


def _owner_cancelled(payload: Mapping[str, object]) -> bool:
    return payload.get(PAYLOAD_REASON) == REASON_OWNER_CANCELLED


def _reopened_kind(payload: Mapping[str, object]) -> str | None:
    if payload.get(PAYLOAD_REASON) in _REOPEN_REASONS:
        return KIND_REVIEW_REOPENED
    return None


def _closed_kind(payload: Mapping[str, object]) -> str | None:
    if payload.get(PAYLOAD_REASON) in _CLOSE_REASONS:
        return KIND_ESCALATION_CLOSED
    return None


__all__ = ["state_kind"]
