"""Turn a Telegram update JSON object into a typed command. No I/O."""

from __future__ import annotations

import hmac
from dataclasses import dataclass

from rag_backend.modules.autopilot.constants import TEXT_ENCODING
from rag_backend.modules.autopilot.webhook_constants import (
    KEY_CALLBACK_QUERY,
    KEY_CHAT,
    KEY_DATA,
    KEY_FROM,
    KEY_ID,
    KEY_MESSAGE,
    KEY_MESSAGE_ID,
    KEY_TEXT,
    KEY_UPDATE_ID,
    KIND_CALLBACK,
    KIND_IGNORED,
    KIND_MESSAGE,
)


@dataclass(frozen=True, kw_only=True)
class WebhookUpdate:
    """One Telegram update after the secret check. Untrusted fields are typed."""

    update_id: int
    kind: str
    actor_id: str = ""
    chat_id: str = ""
    callback_id: str = ""
    data: str = ""
    message_id: int | None = None
    text: str = ""


def secrets_match(provided: str, expected: str) -> bool:
    """Constant-time compare. An empty expected secret matches nothing."""
    if not expected:
        return False
    left = provided.encode(TEXT_ENCODING)
    right = expected.encode(TEXT_ENCODING)
    return hmac.compare_digest(left, right)


def is_owner(actor_id: str, owner_chat_id: str) -> bool:
    """True when ``from.id`` equals the configured owner. Empty owner matches nobody."""
    return secrets_match(actor_id, owner_chat_id.strip())


def parse_webhook_body(raw: object) -> WebhookUpdate | None:
    """Read a callback or a text message. Other shapes stay ignored."""
    if not isinstance(raw, dict):
        return None
    update_id = _int(raw.get(KEY_UPDATE_ID))
    if update_id is None or update_id < 0:
        return None
    callback = raw.get(KEY_CALLBACK_QUERY)
    if isinstance(callback, dict):
        return _callback(update_id, callback)
    message = raw.get(KEY_MESSAGE)
    if isinstance(message, dict):
        return _message(update_id, message)
    return WebhookUpdate(update_id=update_id, kind=KIND_IGNORED)


def _callback(update_id: int, body: dict[str, object]) -> WebhookUpdate:
    message = body.get(KEY_MESSAGE)
    message_body = message if isinstance(message, dict) else {}
    return WebhookUpdate(
        update_id=update_id,
        kind=KIND_CALLBACK,
        actor_id=_actor(body.get(KEY_FROM)),
        chat_id=_chat(message_body.get(KEY_CHAT)),
        callback_id=_text(body.get(KEY_ID)),
        data=_text(body.get(KEY_DATA)),
        message_id=_int(message_body.get(KEY_MESSAGE_ID)),
    )


def _message(update_id: int, body: dict[str, object]) -> WebhookUpdate:
    return WebhookUpdate(
        update_id=update_id,
        kind=KIND_MESSAGE,
        actor_id=_actor(body.get(KEY_FROM)),
        chat_id=_chat(body.get(KEY_CHAT)),
        text=_text(body.get(KEY_TEXT)),
    )


def _actor(raw: object) -> str:
    if not isinstance(raw, dict):
        return ""
    user_id = _int(raw.get(KEY_ID))
    if user_id is None:
        return ""
    return str(user_id)


def _chat(raw: object) -> str:
    if not isinstance(raw, dict):
        return ""
    chat_id = _int(raw.get(KEY_ID))
    if chat_id is None:
        return ""
    return str(chat_id)


def _text(raw: object) -> str:
    if isinstance(raw, str):
        return raw
    return ""


def _int(raw: object) -> int | None:
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    return raw
