"""Telegram reply client and setWebhook helper (AE-0356)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from rag_backend.modules.autopilot.domain.messages import InlineButton, InlineKeyboard
from rag_backend.modules.autopilot.domain.notice_log import (
    NoticeLog,
    StoredPending,
    dump_log,
    notice_log_is_empty,
    parse_stored,
    record_status,
    set_pending,
)
from rag_backend.modules.autopilot.domain.owner_ports import (
    CallbackAnswer,
    ForceReplyPrompt,
    MessageEdit,
    OwnerText,
)
from rag_backend.modules.autopilot.infrastructure.telegram_reply import (
    ReplyClientConfig,
    TelegramOwnerMessenger,
)
from rag_backend.modules.autopilot.scripts.set_webhook import main, set_webhook_body

_TOKEN = "123:abc"


def test_pending_survives_a_status_and_round_trips() -> None:
    pending = StoredPending(owner_chat_id="42", phase="images")
    stored = set_pending(NoticeLog(), pending)
    assert notice_log_is_empty(stored) is False
    kept = record_status(stored, "published", 7)
    assert kept.pending == pending
    parsed = parse_stored(dump_log(kept))
    assert parsed.pending == pending


def test_set_webhook_body_sends_secret_and_allowed_updates() -> None:
    body = set_webhook_body("https://example.com/api/telegram/webhook", "s3cret")
    assert body["url"] == "https://example.com/api/telegram/webhook"
    assert body["secret_token"] == "s3cret"
    assert body["allowed_updates"] == ["message", "callback_query"]


def test_set_webhook_requires_token_and_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "rag_backend.modules.autopilot.scripts.set_webhook.get_settings",
        lambda: SimpleNamespace(
            telegram_bot_token=SecretStr(""),
            telegram_webhook_secret=SecretStr("s3cret"),
        ),
    )
    assert main(["https://example.com/api/telegram/webhook"]) == 1


def test_set_webhook_reports_transport_and_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "rag_backend.modules.autopilot.scripts.set_webhook.get_settings",
        _settings,
    )

    def _down(url: str, json: dict[str, object], timeout: float) -> httpx.Response:
        del url, json, timeout
        raise httpx.ConnectError("down")

    monkeypatch.setattr(
        "rag_backend.modules.autopilot.scripts.set_webhook.httpx.post",
        _down,
    )
    assert main(["https://example.com/api/telegram/webhook"]) == 1

    def _rejected(url: str, json: dict[str, object], timeout: float) -> httpx.Response:
        request = httpx.Request("POST", url)
        del json, timeout
        return httpx.Response(200, json={"ok": False}, request=request)

    monkeypatch.setattr(
        "rag_backend.modules.autopilot.scripts.set_webhook.httpx.post",
        _rejected,
    )
    assert main(["https://example.com/api/telegram/webhook"]) == 1


def test_set_webhook_usage_needs_a_url() -> None:
    assert main([]) == 2
    assert main([""]) == 2


def test_set_webhook_posts_without_printing_the_token(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "rag_backend.modules.autopilot.scripts.set_webhook.get_settings",
        _settings,
    )
    seen: dict[str, object] = {}

    def _post(url: str, json: dict[str, object], timeout: float) -> httpx.Response:
        del timeout
        seen["url"] = url
        seen["body"] = json
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"ok": True}, request=request)

    monkeypatch.setattr(
        "rag_backend.modules.autopilot.scripts.set_webhook.httpx.post",
        _post,
    )
    assert main(["https://example.com/api/telegram/webhook"]) == 0
    captured = capsys.readouterr()
    assert _TOKEN not in captured.out
    assert _TOKEN not in captured.err
    posted = seen["body"]
    assert isinstance(posted, dict)
    assert posted["secret_token"] == "s3cret"
    posted_url = seen["url"]
    assert isinstance(posted_url, str)
    assert _TOKEN in posted_url


@pytest.mark.asyncio
async def test_reply_posts_answer_edit_ask_and_tell() -> None:
    seen: list[tuple[str, dict[str, object]]] = []
    messenger = TelegramOwnerMessenger(
        ReplyClientConfig(token=_TOKEN, client=_http(seen))
    )
    keyboard = InlineKeyboard(
        rows=((InlineButton(text="Text", callback_data="ap:rw:text:x"),),)
    )
    await messenger.answer(CallbackAnswer(callback_id="cb", text="Approved"))
    await messenger.edit(
        MessageEdit(
            chat_id="42", message_id=9, text="Approved. Publishing.", keyboard=keyboard
        )
    )
    await messenger.ask(ForceReplyPrompt(chat_id="42", text="What should change?"))
    await messenger.tell(OwnerText(chat_id="42", text="Reworking images."))
    methods = [path.rsplit("/", 1)[-1] for path, _body in seen]
    assert methods == [
        "answerCallbackQuery",
        "editMessageText",
        "sendMessage",
        "sendMessage",
    ]
    markup = seen[1][1]["reply_markup"]
    assert isinstance(markup, dict)
    assert markup["inline_keyboard"][0][0]["text"] == "Text"
    assert seen[2][1]["reply_markup"] == {"force_reply": True, "selective": True}


@pytest.mark.asyncio
async def test_empty_token_and_http_error_do_not_raise() -> None:
    seen: list[tuple[str, dict[str, object]]] = []
    quiet = TelegramOwnerMessenger(ReplyClientConfig(token="", client=_http(seen)))
    await quiet.answer(CallbackAnswer(callback_id="cb", text="Approved"))
    assert seen == []
    failing = TelegramOwnerMessenger(
        ReplyClientConfig(token=_TOKEN, client=_http(seen, status=500))
    )
    await failing.tell(OwnerText(chat_id="42", text="hello"))


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        telegram_bot_token=SecretStr(_TOKEN),
        telegram_webhook_secret=SecretStr("s3cret"),
    )


def _http(
    seen: list[tuple[str, dict[str, object]]],
    status: int = 200,
) -> httpx.AsyncClient:
    def _handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        seen.append((str(request.url), body))
        return httpx.Response(status, json={"ok": status == 200})

    return httpx.AsyncClient(transport=httpx.MockTransport(_handle))
