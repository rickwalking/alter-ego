"""Scout-failed delivery decisions (AE-0360).

Gherkin: tests/features/autopilot_grok_bot_scout.feature
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rag_backend.modules.autopilot.application.scout_failure import (
    ScoutFailureCommand,
    ScoutFailureDependencies,
    ScoutFailureService,
    failure_text,
    without_urls,
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
from rag_backend.modules.autopilot.domain.scout_ports import ScoutFailureEntry
from rag_backend.modules.autopilot.notify_constants import LOG_NOTIFIER_UNCONFIGURED
from rag_backend.modules.autopilot.scout_constants import (
    DETAIL_SCOUT_DAILY_CAP,
    DETAIL_SCOUT_DUPLICATE,
)

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


_NOW = datetime(2026, 10, 14, 12, tzinfo=UTC)


class _Clock:
    def now(self) -> datetime:
        return _NOW


class _Log:
    def __init__(self, reasons: tuple[str, ...] = ()) -> None:
        self.reasons = list(reasons)
        self.since: datetime | None = None
        self.commits = 0

    async def reasons_since(self, since: datetime) -> tuple[str, ...]:
        self.since = since
        return tuple(self.reasons)

    async def record(self, entry: ScoutFailureEntry) -> None:
        self.reasons.append(entry.reason)

    async def commit(self) -> None:
        self.commits += 1


def _service(
    notifier: _Recorder, chat_id: str = "4242", log: _Log | None = None
) -> ScoutFailureService:
    deps = ScoutFailureDependencies(
        notifier=notifier,
        chat_id=chat_id,
        log=log or _Log(),
        clock=_Clock(),
    )
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


# Scenario: Scout failure reason carries a URL
@pytest.mark.asyncio
async def test_urls_are_stripped_from_the_reason() -> None:
    """URLs never reach Telegram; the rest of the reason does."""
    recorder = _Recorder()
    reason = "login expired see https://evil.example/x and www.evil.example now"
    result = await _service(recorder).report(ScoutFailureCommand(reason=reason))
    assert result.delivered is True
    assert recorder.notices[0].text == failure_text("login expired see and now")
    assert "evil" not in recorder.notices[0].text


# Scenario: Scout failure reason carries a URL
@pytest.mark.asyncio
async def test_url_only_reason_is_rejected() -> None:
    """A reason that is only a URL strips to empty and is rejected."""
    recorder = _Recorder()
    result = await _service(recorder).report(
        ScoutFailureCommand(reason="https://evil.example/x")
    )
    assert result.error == DETAIL_SCOUT_REASON_EMPTY
    assert recorder.notices == []


def test_without_urls_keeps_plain_text() -> None:
    """Plain words, including bare domains, are kept."""
    assert without_urls("x.com login expired") == "x.com login expired"


# Scenario: A fourth scout failure in one day is not sent
@pytest.mark.asyncio
async def test_fourth_failure_in_a_day_is_suppressed() -> None:
    """Three distinct reasons were already delivered in the last 24 hours."""
    recorder = _Recorder()
    log = _Log(("one", "two", "three"))
    result = await _service(recorder, log=log).report(
        ScoutFailureCommand(reason="four")
    )
    assert result.delivered is False
    assert result.error == DETAIL_SCOUT_DAILY_CAP
    assert recorder.notices == []
    assert log.since == datetime(2026, 10, 13, 12, tzinfo=UTC)


# Scenario: A repeated scout failure is not sent twice
@pytest.mark.asyncio
async def test_duplicate_reason_is_suppressed() -> None:
    """The same reason within the window is delivered once."""
    recorder = _Recorder()
    log = _Log((_REASON,))
    result = await _service(recorder, log=log).report(
        ScoutFailureCommand(reason=_REASON)
    )
    assert result.error == DETAIL_SCOUT_DUPLICATE
    assert recorder.notices == []


@pytest.mark.asyncio
async def test_delivered_failure_is_recorded_and_committed() -> None:
    """Only a delivered failure counts toward the cap."""
    recorder = _Recorder()
    log = _Log()
    await _service(recorder, log=log).report(ScoutFailureCommand(reason=_REASON))
    assert log.reasons == [_REASON]
    assert log.commits == 1


@pytest.mark.asyncio
async def test_failed_send_is_not_recorded() -> None:
    """A transport failure leaves the cap untouched so a retry can deliver."""
    log = _Log()
    await _service(_Recorder(TelegramDeliveryError("x")), log=log).report(
        ScoutFailureCommand(reason=_REASON)
    )
    assert log.reasons == []
