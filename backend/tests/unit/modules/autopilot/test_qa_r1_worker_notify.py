"""Worker-tick isolation, deferred webhook replies, and notifier fixes (QA r1).

Gherkin:
  tests/features/autopilot_runner.feature
  tests/features/autopilot_owner_actions.feature
  tests/features/autopilot_telegram_notify.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import cast

import pytest

from rag_backend.application.workers import workflow_workers
from rag_backend.modules.autopilot.application.deferred_replies import (
    DeferredOwnerMessenger,
)
from rag_backend.modules.autopilot.constants import (
    EVENT_TYPE_STATE_CHANGED,
    PAYLOAD_REASON,
    PAYLOAD_STATE,
)
from rag_backend.modules.autopilot.domain.messages import review_keyboard
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.notice_log import bump_attempt
from rag_backend.modules.autopilot.domain.notify import SaveNoticeLog
from rag_backend.modules.autopilot.domain.owner_ports import (
    CallbackAnswer,
    ForceReplyPrompt,
    MessageEdit,
    OwnerText,
)
from rag_backend.modules.autopilot.notify_constants import (
    ATTEMPT_STATUS_PREFIX,
    NOTIFY_MAX_ATTEMPTS,
    TEXT_EXPIRED,
)
from rag_backend.modules.autopilot.recovery_constants import (
    REASON_OWNER_EXPIRED,
    REASON_REWORK_RETRY,
)
from rag_backend.modules.autopilot.domain.exceptions import TelegramDeliveryError
from tests.unit.application.test_workflow_workers import (
    _FakeSession,
    _NoopAlerts,
    _NoopAutoRejector,
    _NoopNotifications,
    _settings,
)
from tests.unit.modules.autopilot.test_owner_notifications import (
    _event,
    _Events,
    _Notifier,
    _run,
    _Runs,
    _service,
)

# --- Worker isolation -------------------------------------------------------


class _Step:
    def __init__(self, log: list[str], name: str, error: bool = False) -> None:
        self._log = log
        self._name = name
        self._error = error

    async def tick(self, _db: object) -> int:
        self._log.append(self._name)
        if self._error:
            raise RuntimeError(self._name)
        return 1


class _Reaper:
    async def tick(self, _db: object) -> int:
        return 3


# Scenario: An autopilot failure does not roll back the other worker steps
@pytest.mark.asyncio
async def test_failing_autopilot_step_rolls_back_alone() -> None:
    log: list[str] = []
    session = _FakeSession()
    collaborators = workflow_workers._TickCollaborators(
        notifications=cast(object, _NoopNotifications()),
        alerts=cast(object, _NoopAlerts()),
        auto_rejector=cast(object, _NoopAutoRejector()),
        stale_run_reaper=cast(object, _Reaper()),
        drift_reconciler=None,
        republish_sweeper=None,
        instagram_publish=cast(object, _Step(log, "instagram")),
        autopilot_runner=cast(object, _Step(log, "autopilot", error=True)),
        telegram_notify=cast(object, _Step(log, "telegram")),
    )

    counters = await workflow_workers._run_tick(
        _settings(autopilot_enabled=True), cast(object, session), collaborators
    )

    assert log == ["instagram", "autopilot", "telegram"]
    assert counters["reaped"] == 3
    assert counters["autopilot_runs"] == 0
    assert counters["telegram_notices"] == 1
    # Core commit, instagram commit, telegram commit; one rollback for autopilot.
    assert session.commits == 3
    assert session.rollbacks == 1


# --- Deferred webhook replies -----------------------------------------------


@dataclass
class _Sink:
    calls: list[str] = field(default_factory=list)

    async def answer(self, command: CallbackAnswer) -> None:
        self.calls.append(f"answer:{command.text}")

    async def edit(self, command: MessageEdit) -> None:
        self.calls.append(f"edit:{command.text}")

    async def ask(self, command: ForceReplyPrompt) -> None:
        self.calls.append(f"ask:{command.text}")

    async def tell(self, command: OwnerText) -> None:
        self.calls.append(f"tell:{command.text}")


# Scenario: Webhook failure after Telegram side effects
@pytest.mark.asyncio
async def test_replies_wait_for_deliver_and_keep_their_order() -> None:
    sink = _Sink()
    deferred = DeferredOwnerMessenger(sink)
    await deferred.answer(CallbackAnswer(callback_id="cb", text="a"))
    await deferred.edit(MessageEdit(chat_id="1", message_id=2, text="e", keyboard=None))
    await deferred.ask(ForceReplyPrompt(chat_id="1", text="q"))
    await deferred.tell(OwnerText(chat_id="1", text="t"))
    assert sink.calls == []

    assert await deferred.deliver() == 4

    assert sink.calls == ["answer:a", "edit:e", "ask:q", "tell:t"]
    assert await deferred.deliver() == 0


@pytest.mark.asyncio
async def test_discarded_replies_are_dropped() -> None:
    sink = _Sink()
    deferred = DeferredOwnerMessenger(sink)
    await deferred.tell(OwnerText(chat_id="1", text="t"))
    assert deferred.discard() == 1
    assert await deferred.deliver() == 0
    assert sink.calls == []


# --- Notifier: expired, reopened, cursor -----------------------------------


@dataclass
class _LedgerStore:
    """Writes the notice ledger back onto the fake run, like the SQL store."""

    runs: _Runs

    async def save(self, command: SaveNoticeLog) -> None:
        run = self.runs.run
        if run is not None and run.run_id == command.run_id:
            self.runs.run = replace(run, notice_log=command.log)


def _state_event(state: str, reason: str, event_id: str) -> object:
    return _event(
        EVENT_TYPE_STATE_CHANGED,
        {PAYLOAD_STATE: state, PAYLOAD_REASON: reason},
        event_id=event_id,
    )


# Scenario: Expired review notice
@pytest.mark.asyncio
async def test_expired_run_tells_the_owner() -> None:
    events = _Events(
        items=[_state_event("expired", REASON_OWNER_EXPIRED, "evt-expired")]
    )
    runs = _Runs(run=_run(AutopilotRunState.EXPIRED))
    notifier = _Notifier()
    service, _store = _service(events, runs, notifier)

    assert await service.tick() == 1
    assert notifier.statuses[0].text == TEXT_EXPIRED
    assert notifier.statuses[0].keyboard is None


# Scenario: Review reopened without regeneration sends the keyboard again
@pytest.mark.asyncio
async def test_reopened_review_sends_the_keyboard_again() -> None:
    events = _Events(
        items=[_state_event("awaiting_owner", REASON_REWORK_RETRY, "evt-reopen")]
    )
    run = _run(AutopilotRunState.AWAITING_OWNER)
    notifier = _Notifier()
    service, _store = _service(events, _Runs(run=run), notifier)

    assert await service.tick() == 1
    assert REASON_REWORK_RETRY in notifier.statuses[0].text
    assert notifier.statuses[0].keyboard == review_keyboard(run.run_id)


@pytest.mark.asyncio
async def test_plain_return_to_owner_sends_no_status() -> None:
    events = _Events(items=[_state_event("awaiting_owner", "ready_for_owner", "e")])
    notifier = _Notifier()
    service, _store = _service(events, _Runs(run=_run()), notifier)
    assert await service.tick() == 0
    assert notifier.statuses == []


# Scenario: Undelivered notices are processed oldest first and never skipped
@pytest.mark.asyncio
async def test_cursor_stops_at_the_first_unsettled_notice() -> None:
    runs = _Runs(run=_run(AutopilotRunState.ESCALATED))
    events = _Events(
        items=[
            _state_event("generating", "generating", "evt-ignored"),
            _state_event("escalated", "phase_failed", "evt-retry"),
            _state_event("failed", "start_failed", "evt-later"),
        ]
    )
    notifier = _Notifier(error=TelegramDeliveryError("telegram_http_500"))
    service, _store = _service(events, runs, notifier)
    service._deps = replace(service._deps, notices=_LedgerStore(runs))

    await service.tick()

    # The ignored event is settled; the failed send is retried later, so the
    # cursor must not pass it even though the next event was also tried.
    assert events.advanced == ["evt-ignored"]


@pytest.mark.asyncio
async def test_cursor_passes_delivered_and_exhausted_notices() -> None:
    exhausted = _run(AutopilotRunState.ESCALATED).notice_log
    for _ in range(NOTIFY_MAX_ATTEMPTS):
        exhausted = bump_attempt(exhausted, f"{ATTEMPT_STATUS_PREFIX}evt-dead")
    run: AutopilotRun = replace(
        _run(AutopilotRunState.ESCALATED), notice_log=exhausted
    )
    runs = _Runs(run=run)
    events = _Events(
        items=[
            _state_event("escalated", "phase_failed", "evt-dead"),
            _state_event("escalated", "phase_failed", "evt-ok"),
        ]
    )
    notifier = _Notifier()
    service, _store = _service(events, runs, notifier)
    service._deps = replace(service._deps, notices=_LedgerStore(runs))

    assert await service.tick() == 1

    assert events.advanced == ["evt-dead", "evt-ok"]
