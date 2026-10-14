"""respx tests for the Telegram Bot API adapter (AE-0355).

Gherkin: tests/features/autopilot_telegram_notify.feature
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs
from uuid import UUID

import httpx
import pytest
import respx

from rag_backend.modules.autopilot.domain.exceptions import (
    NotifierUnconfiguredError,
    TelegramDeliveryError,
    TelegramRateLimitedError,
)
from rag_backend.modules.autopilot.domain.messages import retry_keyboard
from rag_backend.modules.autopilot.domain.notify import ReviewNotice, StatusNotice
from rag_backend.modules.autopilot.infrastructure.telegram_notifier import (
    AsyncSleeper,
    TelegramClientConfig,
    TelegramNotifier,
)
from rag_backend.modules.autopilot.infrastructure.telegram_payload import (
    accepted_payload,
    group_ids,
    one_id,
    retry_after_seconds,
)
from rag_backend.modules.autopilot.notify_constants import (
    CALLBACK_APPROVE_PREFIX,
    CALLBACK_REJECT_PREFIX,
    CALLBACK_REWORK_PREFIX,
    DETAIL_TRANSPORT,
    LOG_NOTIFIER_UNCONFIGURED,
)

_TOKEN = "test-bot-token"
_CHAT = "42"
_RUN = UUID("22222222-2222-4222-8222-222222222222")
_MEDIA = r"https://api.telegram.org/bot.+/sendMediaGroup$"
_MESSAGE = r"https://api.telegram.org/bot.+/sendMessage$"
_PHOTO = r"https://api.telegram.org/bot.+/sendPhoto$"


class _Sleeper:
    def __init__(self) -> None:
        self.seconds: list[float] = []

    async def sleep(self, seconds: float) -> None:
        self.seconds.append(seconds)


def _jpeg(directory: Path, name: str) -> str:
    path = directory / name
    path.write_bytes(b"\xff\xd8\xff" + b"x" * 16)
    return str(path)


def _review(paths: tuple[str, ...], prior: tuple[int, ...] = ()) -> ReviewNotice:
    return ReviewNotice(
        chat_id=_CHAT,
        run_id=_RUN,
        title="Agents that ship",
        persona_score=88.0,
        sources_count=7,
        caption="A caption " * 120,
        slide_paths=paths,
        prior_album_ids=prior,
    )


def _notifier(sleeper: _Sleeper, token: str = _TOKEN) -> TelegramNotifier:
    return TelegramNotifier(TelegramClientConfig(token=token, sleeper=sleeper))


def _ok_group(count: int) -> httpx.Response:
    result = [{"message_id": index + 1} for index in range(count)]
    return httpx.Response(200, json={"ok": True, "result": result})


def _ok_message(message_id: int) -> httpx.Response:
    return httpx.Response(200, json={"ok": True, "result": {"message_id": message_id}})


@pytest.mark.asyncio
async def test_review_uploads_seven_slides_and_the_keyboard(tmp_path: Path) -> None:
    """Scenario: Owner receives slides and buttons."""
    paths = tuple(_jpeg(tmp_path, f"slide_{index}.jpg") for index in range(1, 8))
    sleeper = _Sleeper()
    with respx.mock(assert_all_called=True) as router:
        group = router.post(url__regex=_MEDIA).mock(return_value=_ok_group(7))
        message = router.post(url__regex=_MESSAGE).mock(return_value=_ok_message(90))
        result = await _notifier(sleeper).send_review(_review(paths))

    assert result.album_ids == (1, 2, 3, 4, 5, 6, 7)
    assert result.keyboard_id == 90
    body = group.calls[0].request.content.decode("latin-1")
    for index in range(7):
        assert f"attach://slide{index}" in body
    assert "https://" not in body
    assert _TOKEN not in body
    form = _form(message.calls[0].request.content)
    markup = json.loads(form["reply_markup"])
    callbacks = [
        button["callback_data"] for row in markup["inline_keyboard"] for button in row
    ]
    assert f"{CALLBACK_APPROVE_PREFIX}{_RUN}" in callbacks
    assert f"{CALLBACK_REWORK_PREFIX}{_RUN}" in callbacks
    assert f"{CALLBACK_REJECT_PREFIX}{_RUN}" in callbacks
    assert len(_review(paths).caption) > 1000
    assert "A caption" in form["text"]


@pytest.mark.asyncio
async def test_rate_limit_waits_retry_after_then_succeeds(tmp_path: Path) -> None:
    """Scenario: Rate limited."""
    paths = (_jpeg(tmp_path, "slide_1.jpg"), _jpeg(tmp_path, "slide_2.jpg"))
    sleeper = _Sleeper()
    limited = httpx.Response(
        429,
        json={"ok": False, "parameters": {"retry_after": 3}},
    )
    with respx.mock(assert_all_called=True) as router:
        router.post(url__regex=_MEDIA).mock(side_effect=[limited, _ok_group(2)])
        router.post(url__regex=_MESSAGE).mock(return_value=_ok_message(8))
        result = await _notifier(sleeper).send_review(_review(paths))

    assert sleeper.seconds == [3.0]
    assert result.album_ids == (1, 2)
    assert result.keyboard_id == 8


@pytest.mark.asyncio
async def test_persistent_rate_limit_does_not_raise_a_counted_failure(
    tmp_path: Path,
) -> None:
    paths = (_jpeg(tmp_path, "slide_1.jpg"), _jpeg(tmp_path, "slide_2.jpg"))
    sleeper = _Sleeper()
    limited = httpx.Response(429, json={"parameters": {"retry_after": 3}})
    with respx.mock(assert_all_called=False) as router:
        router.post(url__regex=_MEDIA).mock(return_value=limited)
        with pytest.raises(TelegramRateLimitedError) as caught:
            await _notifier(sleeper).send_review(_review(paths))
    assert _TOKEN not in str(caught.value)


@pytest.mark.asyncio
async def test_http_error_detail_does_not_contain_the_token(tmp_path: Path) -> None:
    paths = (_jpeg(tmp_path, "slide_1.jpg"), _jpeg(tmp_path, "slide_2.jpg"))
    with respx.mock(assert_all_called=True) as router:
        router.post(url__regex=_MEDIA).mock(return_value=httpx.Response(500))
        with pytest.raises(TelegramDeliveryError) as caught:
            await _notifier(_Sleeper()).send_review(_review(paths))
    assert _TOKEN not in str(caught.value)
    assert "500" in str(caught.value)


@pytest.mark.asyncio
async def test_transport_error_is_redacted() -> None:
    def _boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"failed {request.url}")

    with respx.mock(assert_all_called=False) as router:
        router.post(url__regex=_MESSAGE).mock(side_effect=_boom)
        notice = StatusNotice(
            chat_id=_CHAT,
            run_id=_RUN,
            text="Failed: phase_failed",
            keyboard=None,
        )
        with pytest.raises(TelegramDeliveryError) as caught:
            await _notifier(_Sleeper()).send_status(notice)
    assert str(caught.value) == DETAIL_TRANSPORT
    assert _TOKEN not in str(caught.value)


@pytest.mark.asyncio
async def test_unset_token_logs_and_does_not_call(tmp_path: Path) -> None:
    """Scenario: Missing bot token escalates and does not call Telegram."""
    paths = (_jpeg(tmp_path, "slide_1.jpg"),)
    with respx.mock(assert_all_called=False) as router:
        router.post(url__regex=r"https://api.telegram.org/.*").mock(
            return_value=_ok_message(1)
        )
        with pytest.raises(NotifierUnconfiguredError) as caught:
            await _notifier(_Sleeper(), token="").send_review(_review(paths))
    assert router.calls == []
    assert LOG_NOTIFIER_UNCONFIGURED in str(caught.value)


@pytest.mark.asyncio
async def test_one_slide_uses_send_photo(tmp_path: Path) -> None:
    path = _jpeg(tmp_path, "slide_1.jpg")
    with respx.mock(assert_all_called=True) as router:
        photo = router.post(url__regex=_PHOTO).mock(return_value=_ok_message(4))
        router.post(url__regex=_MESSAGE).mock(return_value=_ok_message(5))
        result = await _notifier(_Sleeper()).send_review(_review((path,)))
    assert result.album_ids == (4,)
    body = photo.calls[0].request.content.decode("latin-1")
    assert "filename" in body or "slide_1.jpg" in body
    assert "sendMediaGroup" not in str(photo.calls[0].request.url)


@pytest.mark.asyncio
async def test_prior_album_skips_the_upload(tmp_path: Path) -> None:
    with respx.mock(assert_all_called=True) as router:
        message = router.post(url__regex=_MESSAGE).mock(return_value=_ok_message(6))
        result = await _notifier(_Sleeper()).send_review(_review((), prior=(11, 12)))
    assert result.album_ids == (11, 12)
    assert result.keyboard_id == 6
    assert message.calls[0].request.url.path.endswith("sendMessage")


@pytest.mark.asyncio
async def test_publish_failed_sends_the_retry_button() -> None:
    """Scenario: Publish failure offers retry."""
    with respx.mock(assert_all_called=True) as router:
        message = router.post(url__regex=_MESSAGE).mock(return_value=_ok_message(15))
        result = await _notifier(_Sleeper()).send_status(
            StatusNotice(
                chat_id=_CHAT,
                run_id=_RUN,
                text="publish failed: 36003",
                keyboard=retry_keyboard(_RUN),
            )
        )
    assert result.message_id == 15
    form = _form(message.calls[0].request.content)
    markup = json.loads(form["reply_markup"])
    callback = markup["inline_keyboard"][0][0]["callback_data"]
    assert callback == f"ap:retry:{_RUN}"
    assert len(callback.encode("utf-8")) <= 64


@pytest.mark.asyncio
async def test_large_retry_after_is_rescheduled(tmp_path: Path) -> None:
    paths = (_jpeg(tmp_path, "slide_1.jpg"), _jpeg(tmp_path, "slide_2.jpg"))
    sleeper = _Sleeper()
    limited = httpx.Response(429, json={"parameters": {"retry_after": 3600}})
    with respx.mock(assert_all_called=False) as router:
        router.post(url__regex=_MEDIA).mock(return_value=limited)
        with pytest.raises(TelegramRateLimitedError):
            await _notifier(sleeper).send_review(_review(paths))
    assert sleeper.seconds == []


@pytest.mark.asyncio
async def test_no_slides_still_sends_the_keyboard() -> None:
    with respx.mock(assert_all_called=True) as router:
        router.post(url__regex=_MESSAGE).mock(return_value=_ok_message(3))
        result = await _notifier(_Sleeper()).send_review(_review(()))
    assert result.album_ids == ()
    assert result.keyboard_id == 3


@pytest.mark.asyncio
async def test_async_sleeper_accepts_a_zero_delay() -> None:
    await AsyncSleeper().sleep(0)


def test_payload_errors_stay_free_of_the_token() -> None:
    denied = httpx.Response(200, json={"ok": False})
    with pytest.raises(TelegramDeliveryError) as caught:
        accepted_payload(denied)
    assert _TOKEN not in str(caught.value)
    broken = httpx.Response(200, content=b"not-json")
    with pytest.raises(TelegramDeliveryError):
        group_ids(accepted_payload(broken))
    with pytest.raises(TelegramDeliveryError):
        group_ids(["nope"])
    assert retry_after_seconds(httpx.Response(429, json=[])) == 1.0
    with pytest.raises(TelegramDeliveryError):
        group_ids({"ok": True, "result": []})
    with pytest.raises(TelegramDeliveryError):
        one_id({"ok": True})
    with pytest.raises(TelegramDeliveryError):
        one_id({"ok": True, "result": {"message_id": True}})
    assert retry_after_seconds(httpx.Response(429, content=b"nope")) == 1.0
    assert retry_after_seconds(httpx.Response(429, json={"parameters": []})) == 1.0
    limited = httpx.Response(429, json={"parameters": {"retry_after": True}})
    assert retry_after_seconds(limited) == 1.0


def _form(content: bytes) -> dict[str, str]:
    parsed = parse_qs(content.decode("utf-8"))
    return {key: values[0] for key, values in parsed.items() if values}
