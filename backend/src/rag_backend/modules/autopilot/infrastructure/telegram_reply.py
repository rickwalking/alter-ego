"""Bot API replies for a webhook: answer, edit, ForceReply, and plain text."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog

from rag_backend.modules.autopilot.domain.owner_ports import (
    CallbackAnswer,
    ForceReplyPrompt,
    MessageEdit,
    OwnerText,
)
from rag_backend.modules.autopilot.infrastructure.telegram_payload import (
    empty_markup,
    force_reply_markup,
    inline_markup,
)
from rag_backend.modules.autopilot.notify_constants import (
    FIELD_CHAT_ID,
    FIELD_MESSAGE_ID,
    FIELD_REPLY_MARKUP,
    FIELD_TEXT,
    TELEGRAM_API_HOST,
    TELEGRAM_HTTP_TIMEOUT_SECONDS,
    TELEGRAM_METHOD_MESSAGE,
)
from rag_backend.modules.autopilot.webhook_constants import (
    FIELD_CALLBACK_QUERY_ID,
    LOG_WEBHOOK_REPLY_FAILED,
    TELEGRAM_METHOD_ANSWER,
    TELEGRAM_METHOD_EDIT_TEXT,
)

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class ReplyClientConfig:
    """Bot token and an optional client. The token is never logged."""

    token: str
    client: httpx.AsyncClient | None = None


class TelegramOwnerMessenger:
    """Best-effort replies. A transport error does not undo the run transition."""

    def __init__(self, config: ReplyClientConfig) -> None:
        self._token = config.token.strip()
        self._client = config.client
        self._owned = config.client is None

    async def answer(self, command: CallbackAnswer) -> None:
        """Stop the button spinner."""
        await self._post(
            TELEGRAM_METHOD_ANSWER,
            {
                FIELD_CALLBACK_QUERY_ID: command.callback_id,
                FIELD_TEXT: command.text,
            },
        )

    async def edit(self, command: MessageEdit) -> None:
        """Replace the keyboard message. An empty keyboard removes the buttons."""
        markup: dict[str, object]
        if command.keyboard is None:
            markup = empty_markup()
        else:
            markup = inline_markup(command.keyboard)
        await self._post(
            TELEGRAM_METHOD_EDIT_TEXT,
            {
                FIELD_CHAT_ID: command.chat_id,
                FIELD_MESSAGE_ID: command.message_id,
                FIELD_TEXT: command.text,
                FIELD_REPLY_MARKUP: markup,
            },
        )

    async def ask(self, command: ForceReplyPrompt) -> None:
        """Send the rework prompt with ForceReply."""
        await self._post(
            TELEGRAM_METHOD_MESSAGE,
            {
                FIELD_CHAT_ID: command.chat_id,
                FIELD_TEXT: command.text,
                FIELD_REPLY_MARKUP: force_reply_markup(),
            },
        )

    async def tell(self, command: OwnerText) -> None:
        """Send one plain text message."""
        await self._post(
            TELEGRAM_METHOD_MESSAGE,
            {FIELD_CHAT_ID: command.chat_id, FIELD_TEXT: command.text},
        )

    async def _post(self, method: str, data: dict[str, object]) -> None:
        if not self._token:
            logger.info(LOG_WEBHOOK_REPLY_FAILED, method=method, reason="no_token")
            return
        client = self._client or httpx.AsyncClient(
            timeout=TELEGRAM_HTTP_TIMEOUT_SECONDS,
        )
        try:
            response = await client.post(_url(self._token, method), json=data)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.info(
                LOG_WEBHOOK_REPLY_FAILED,
                method=method,
                error_type=exc.__class__.__name__,
            )
        finally:
            if self._owned and self._client is None:
                await client.aclose()


def _url(token: str, method: str) -> str:
    return f"{TELEGRAM_API_HOST}/bot{token}/{method}"
