"""Owner cancellation stays durable without becoming a Telegram failure alarm."""

from __future__ import annotations

import pytest

from rag_backend.modules.autopilot.constants import EVENT_TYPE_STATE_CHANGED
from rag_backend.modules.autopilot.domain.messages import notice_kind
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.notify_constants import KIND_FAILED
from tests.unit.modules.autopilot.test_owner_notifications import (
    _event,
    _Events,
    _Notifier,
    _run,
    _Runs,
    _service,
)


def test_only_owner_cancel_failure_has_no_notice_kind() -> None:
    """Scenario: Owner cancellation is audited without a Telegram failure alarm"""
    cancelled = {"state": "failed", "reason": "owner_queue_cancelled"}
    genuine = {"state": "failed", "reason": "phase_failed"}
    assert notice_kind(EVENT_TYPE_STATE_CHANGED, cancelled) is None
    assert notice_kind(EVENT_TYPE_STATE_CHANGED, genuine) == KIND_FAILED


@pytest.mark.asyncio
async def test_cancel_event_advances_without_erasing_outbox_or_genuine_notice() -> None:
    """Scenario: Owner cancellation is audited without a Telegram failure alarm"""
    cancelled = _event(
        EVENT_TYPE_STATE_CHANGED,
        {"state": "failed", "reason": "owner_queue_cancelled"},
        "cancelled",
    )
    genuine = _event(
        EVENT_TYPE_STATE_CHANGED,
        {"state": "failed", "reason": "phase_failed"},
        "genuine",
    )
    events = _Events([cancelled, genuine])
    notifier = _Notifier()
    service, _ = _service(events, _Runs(_run(state=AutopilotRunState.FAILED)), notifier)
    assert await service.tick() == 1
    assert events.advanced == ["cancelled"]
    assert events.items == [cancelled, genuine]
    assert len(notifier.statuses) == 1
    assert "phase_failed" in notifier.statuses[0].text
