"""Send the boost prompt and keep the message id. The token is not logged."""

from __future__ import annotations

import httpx

from rag_backend.modules.autopilot.domain.messages import InlineKeyboard
from rag_backend.modules.autopilot.infrastructure.telegram_payload import (
    inline_markup,
    one_id,
)
from rag_backend.modules.autopilot.notify_constants import (
    FIELD_CHAT_ID,
    FIELD_REPLY_MARKUP,
    FIELD_TEXT,
    TELEGRAM_API_HOST,
    TELEGRAM_HTTP_TIMEOUT_SECONDS,
    TELEGRAM_METHOD_MESSAGE,
)


class TelegramBoostMessenger:
    """``sendMessage`` for a new request. Empty token returns no message id."""

    def __init__(self, token: str, chat_id: str) -> None:
        self._token = token.strip()
        self._chat_id = chat_id

    async def send(self, text: str, keyboard: InlineKeyboard) -> int | None:
        """Return the Telegram message id, or None when the bot is not configured."""
        if not self._token or not self._chat_id:
            return None
        url = f"{TELEGRAM_API_HOST}/bot{self._token}/{TELEGRAM_METHOD_MESSAGE}"
        async with httpx.AsyncClient(timeout=TELEGRAM_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                json={
                    FIELD_CHAT_ID: self._chat_id,
                    FIELD_TEXT: text,
                    FIELD_REPLY_MARKUP: inline_markup(keyboard),
                },
            )
        if not response.is_success:
            return None
        try:
            return one_id(response.json())
        except (ValueError, KeyError, TypeError):
            return None

    async def edit(self, message_id: int, text: str) -> None:
        """The webhook messenger edits. This sender does not."""
        del message_id, text
        if self._token == "":
            return


__all__ = ["TelegramBoostMessenger"]
