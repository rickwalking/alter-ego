"""Scout-failed delivery decisions (AE-0360).

Gherkin: tests/features/autopilot_grok_bot_scout.feature
"""

from __future__ import annotations

import pytest

from rag_backend.modules.autopilot.application.scout_failure import (
    ScoutFailureCommand,
    ScoutFailureDependencies,
    ScoutFailureService,
    failure_text,
)
from rag_backend.modules.autopilot.constants import (
    DETAIL_SCOUT_NOTIFY_FAILED,
    DETAIL_SCOUT_NOTIFY_UNCONFIGURED,
    DETAIL_SCOUT_REASON_EMPTY,
    SCOUT_FAILED_PREFIX,
)
from rag_backend.modules.autopilot.domain.exceptions import (
    NotifierUnconfiguredError,
    TelegramDeliveryError,
    TelegramRateLimitedError,
)
from rag_backend.modules.autopilot.domain.notify import StatusNotice, StatusSendResult
from rag_backend.modules.autopilot.notify_constants import LOG_NOTIFIER_UNCONFIGURED

_REASON = "x.com login expired"


class _Recorder:
    def __init__(self, error: Exception | None = None) -> None:
        self.notices: list[StatusNotice] = []
        self._error = error

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        if self._error is not None:
            raise self._error
        self.notices.append(notice)
        return StatusSendResult(message_id=9)


def _service(notifier: _Recorder, chat_id: str = "4242") -> ScoutFailureService:
    deps = ScoutFailureDependencies(notifier=notifier, chat_id=chat_id)
    return ScoutFailureService(deps)


@pytest.mark.asyncio
async def test_owner_receives_one_message_containing_the_reason() -> None:
    """Scenario: Scout reports a failure."""
    recorder = _Recorder()
    result = await _service(recorder).report(ScoutFailureCommand(reason=_REASON))
    assert result.delivered is True
    assert result.error is None
    assert len(recorder.notices) == 1
    assert recorder.notices[0].text == failure_text(_REASON)
    assert _REASON in recorder.notices[0].text
    assert recorder.notices[0].text.startswith(SCOUT_FAILED_PREFIX)
    assert recorder.notices[0].chat_id == "4242"
    assert recorder.notices[0].keyboard is None


@pytest.mark.asyncio
async def test_control_only_reason_sends_nothing() -> None:
    """A reason that strips to empty is a client error and is not delivered."""
    recorder = _Recorder()
    result = await _service(recorder).report(ScoutFailureCommand(reason="\x00"))
    assert result.delivered is False
    assert result.error == DETAIL_SCOUT_REASON_EMPTY
    assert recorder.notices == []


@pytest.mark.asyncio
async def test_missing_chat_sends_nothing() -> None:
    """An empty owner chat id cannot deliver."""
    recorder = _Recorder()
    result = await _service(recorder, chat_id="  ").report(
        ScoutFailureCommand(reason=_REASON)
    )
    assert result.error == DETAIL_SCOUT_NOTIFY_UNCONFIGURED
    assert recorder.notices == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        NotifierUnconfiguredError(LOG_NOTIFIER_UNCONFIGURED),
        TelegramDeliveryError("transport"),
        TelegramRateLimitedError("limited"),
    ],
)
async def test_notifier_errors_are_not_delivered(error: Exception) -> None:
    """Transport and configuration failures stay on the result, not the chat."""
    recorder = _Recorder(error)
    result = await _service(recorder).report(ScoutFailureCommand(reason=_REASON))
    assert result.delivered is False
    assert recorder.notices == []
    if isinstance(error, NotifierUnconfiguredError):
        assert result.error == DETAIL_SCOUT_NOTIFY_UNCONFIGURED
        return
    assert result.error == DETAIL_SCOUT_NOTIFY_FAILED
