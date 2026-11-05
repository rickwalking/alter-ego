"""The claim around a re-sent notice, and what counts as not sent.

Feature: tests/features/scan_escalation_renotice_ae0618.feature
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest

from rag_backend.modules.autopilot.application.renotice_send import status_sender
from rag_backend.modules.autopilot.domain.exceptions import (
    NotifierUnconfiguredError,
    RenoticeClaimedError,
    TelegramDeliveryError,
    TelegramDeliveryUnknownError,
    TelegramRateLimitedError,
)
from rag_backend.modules.autopilot.domain.notify import (
    AutopilotOutboxEvent,
    ReviewNotice,
    ReviewSendResult,
    StatusNotice,
    StatusSendResult,
)
from rag_backend.modules.autopilot.infrastructure.telegram_notifier import (
    AsyncSleeper,
    TelegramClientConfig,
    TelegramNotifier,
)

_RENOTICE = "content.autopilot.escalation_renotice"
_STATE_CHANGED = "content.autopilot.state_changed"


@dataclass
class _Claims:
    free: bool = True
    calls: list[tuple[str, UUID, str]] = field(default_factory=list)

    async def take(self, run_id: UUID, event_id: str) -> bool:
        self.calls.append(("take", run_id, event_id))
        return self.free

    async def release(self, run_id: UUID, event_id: str) -> None:
        self.calls.append(("release", run_id, event_id))


@dataclass
class _Notifier:
    error: Exception | None = None
    sent: list[StatusNotice] = field(default_factory=list)

    async def send_review(self, notice: ReviewNotice) -> ReviewSendResult:
        raise AssertionError(notice)

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        self.sent.append(notice)
        if self.error is not None:
            raise self.error
        return StatusSendResult(message_id=1)


def _event(event_type: str = _RENOTICE) -> AutopilotOutboxEvent:
    return AutopilotOutboxEvent(
        event_id="e1",
        event_type=event_type,
        run_id=uuid4(),
        payload={},
        created_at=datetime(2026, 11, 5, tzinfo=UTC),
    )


def _notice(event: AutopilotOutboxEvent) -> StatusNotice:
    return StatusNotice(chat_id="c", run_id=event.run_id, text="t", keyboard=None)


async def test_any_other_event_goes_straight_to_the_notifier() -> None:
    event = _event(_STATE_CHANGED)
    notifier, claims = _Notifier(), _Claims()
    sender = status_sender(notifier, claims, event)
    assert sender is notifier
    assert claims.calls == []


async def test_a_successful_send_keeps_the_claim() -> None:
    """Scenario: A crash after the send never sends the notice twice"""
    event = _event()
    notifier, claims = _Notifier(), _Claims()
    result = await status_sender(notifier, claims, event).send_status(_notice(event))
    assert result.message_id == 1
    assert claims.calls == [("take", event.run_id, "e1")]


async def test_a_notice_someone_else_claimed_is_not_sent() -> None:
    """Scenario: A second worker cannot take a send in flight"""
    event = _event()
    notifier, claims = _Notifier(), _Claims(free=False)
    with pytest.raises(RenoticeClaimedError):
        await status_sender(notifier, claims, event).send_status(_notice(event))
    assert notifier.sent == []


@pytest.mark.parametrize(
    "error",
    [
        TelegramDeliveryError("status 500"),
        TelegramRateLimitedError("limited"),
        NotifierUnconfiguredError(),
    ],
    ids=["refused", "rate limited", "unconfigured"],
)
async def test_a_send_that_did_not_happen_releases_the_claim(error: Exception) -> None:
    """Scenario: A rate limited send stays open"""
    event = _event()
    claims = _Claims()
    sender = status_sender(_Notifier(error=error), claims, event)
    with pytest.raises(type(error)):
        await sender.send_status(_notice(event))
    assert claims.calls == [
        ("take", event.run_id, "e1"),
        ("release", event.run_id, "e1"),
    ]


@pytest.mark.parametrize(
    "error",
    [TelegramDeliveryUnknownError("transport"), RuntimeError("boom")],
    ids=["unknown outcome", "anything else"],
)
async def test_a_send_with_an_unknown_outcome_keeps_the_claim(
    error: Exception,
) -> None:
    """Scenario: A send with an unknown outcome is never repeated"""
    event = _event()
    claims = _Claims()
    sender = status_sender(_Notifier(error=error), claims, event)
    with pytest.raises(type(error)):
        await sender.send_status(_notice(event))
    assert claims.calls == [("take", event.run_id, "e1")]


def _telegram(error: Exception) -> TelegramNotifier:
    def fail(request: httpx.Request) -> httpx.Response:
        raise error

    return _client(fail)


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> TelegramNotifier:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    config = TelegramClientConfig(token="t", sleeper=AsyncSleeper(), client=client)
    return TelegramNotifier(config)


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("refused"),
        httpx.ConnectTimeout("slow"),
        httpx.PoolTimeout("busy"),
    ],
    ids=["refused", "connect timeout", "pool timeout"],
)
async def test_a_refused_connection_is_a_plain_failure(error: Exception) -> None:
    """Scenario: A refused connection counts as not sent"""
    with pytest.raises(TelegramDeliveryError) as caught:
        await _telegram(error).send_status(_notice(_event()))
    assert not isinstance(caught.value, TelegramDeliveryUnknownError)


@pytest.mark.parametrize(
    "error",
    [
        httpx.ReadTimeout("late"),
        httpx.WriteTimeout("late"),
        httpx.ReadError("cut"),
        httpx.RemoteProtocolError("cut"),
    ],
    ids=["read timeout", "write timeout", "read error", "protocol error"],
)
async def test_a_failure_after_the_request_left_is_unknown(error: Exception) -> None:
    """Scenario: A timeout after the request left counts as unknown"""
    with pytest.raises(TelegramDeliveryUnknownError):
        await _telegram(error).send_status(_notice(_event()))


def test_an_unknown_outcome_is_still_a_delivery_failure() -> None:
    """Scenario: A send with an unknown outcome is never repeated"""
    assert issubclass(TelegramDeliveryUnknownError, TelegramDeliveryError)


_UNREADABLE = [
    pytest.param("no json", id="not json"),
    pytest.param("{}", id="empty object"),
    pytest.param('{"ok": true}', id="no result"),
    pytest.param('{"ok": true, "result": {}}', id="no message id"),
    pytest.param('{"ok": true, "result": {"message_id": "7"}}', id="bad id"),
    pytest.param('{"ok": true, "result": []}', id="result is a list"),
    pytest.param("[]", id="json list"),
    pytest.param('{"ok": false}', id="ok false"),
]


def _answers(body: str) -> TelegramNotifier:
    return _client(lambda request: httpx.Response(200, text=body))


@pytest.mark.parametrize("body", _UNREADABLE)
async def test_an_unreadable_success_is_unknown(body: str) -> None:
    """Scenario Outline: A successful answer that cannot be read counts as unknown"""
    with pytest.raises(TelegramDeliveryUnknownError):
        await _answers(body).send_status(_notice(_event()))


@pytest.mark.parametrize("body", _UNREADABLE)
async def test_an_unreadable_success_keeps_the_claim(body: str) -> None:
    """Scenario Outline: A successful answer that cannot be read counts as unknown"""
    event = _event()
    claims = _Claims()
    sender = status_sender(_answers(body), claims, event)
    with pytest.raises(TelegramDeliveryUnknownError):
        await sender.send_status(_notice(event))
    assert claims.calls == [("take", event.run_id, "e1")]


async def test_an_error_status_is_still_a_plain_failure() -> None:
    """Scenario: A refused connection counts as not sent"""
    denied = _client(lambda request: httpx.Response(400, text='{"ok": false}'))
    with pytest.raises(TelegramDeliveryError) as caught:
        await denied.send_status(_notice(_event()))
    assert not isinstance(caught.value, TelegramDeliveryUnknownError)
