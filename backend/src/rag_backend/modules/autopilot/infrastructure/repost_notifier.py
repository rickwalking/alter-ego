"""Telegram delivery of a repost draft: cover photo, preview video, prompt.

The prompt (with the buttons) is a text message sent last, so a decision can
edit it with ``editMessageText``. A preview over Telegram's upload limit is
replaced by its public link inside the prompt. The token is never logged.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from rag_backend.modules.autopilot.domain.messages import InlineKeyboard
from rag_backend.modules.autopilot.infrastructure.telegram_payload import (
    cover_photo_file,
    inline_markup,
    one_id,
)
from rag_backend.modules.autopilot.notify_constants import (
    FIELD_CAPTION,
    FIELD_CHAT_ID,
    FIELD_MESSAGE_ID,
    FIELD_REPLY_MARKUP,
    FIELD_TEXT,
    TELEGRAM_API_HOST,
    TELEGRAM_HTTP_TIMEOUT_SECONDS,
    TELEGRAM_METHOD_MESSAGE,
    TELEGRAM_METHOD_PHOTO,
)
from rag_backend.modules.autopilot.repost_constants import (
    MEDIA_TYPE_MP4,
    TELEGRAM_FIELD_SUPPORTS_STREAMING,
    TELEGRAM_FIELD_VIDEO,
    TELEGRAM_METHOD_VIDEO,
    TELEGRAM_UPLOAD_TIMEOUT_SECONDS,
    TELEGRAM_VIDEO_MAX_BYTES,
    TEXT_COVER_CAPTION,
    TEXT_PREVIEW_CAPTION,
)
from rag_backend.modules.autopilot.webhook_constants import TELEGRAM_METHOD_EDIT_TEXT

_TRUE = "true"


@dataclass(frozen=True, kw_only=True)
class PreviewMessage:
    """The files to show and the prompt with its buttons."""

    cover_path: Path | None
    video_path: Path | None
    text: str
    keyboard: InlineKeyboard


def fits_telegram(video_path: Path) -> bool:
    """True when the preview can be uploaded as a bot video."""
    return video_path.stat().st_size <= TELEGRAM_VIDEO_MAX_BYTES


class TelegramRepostMessenger:
    """Sends the preview and the prompt; returns the prompt's message id."""

    def __init__(self, token: str, chat_id: str) -> None:
        self._token = token.strip()
        self._chat_id = chat_id

    @property
    def configured(self) -> bool:
        """True with a bot token and an owner chat."""
        return bool(self._token and self._chat_id)

    async def send_preview(self, message: PreviewMessage) -> int | None:
        """Cover, video, then the prompt. None when the prompt was not accepted."""
        if not self.configured:
            return None
        async with httpx.AsyncClient(timeout=TELEGRAM_UPLOAD_TIMEOUT_SECONDS) as client:
            if message.cover_path is not None:
                await self._photo(client, message.cover_path)
            if message.video_path is not None:
                await self._video(client, message.video_path)
            return await self._prompt(client, message)

    async def edit(self, message_id: int, text: str) -> None:
        """Replace the prompt's text and drop its buttons."""
        if not self.configured:
            return
        async with httpx.AsyncClient(timeout=TELEGRAM_HTTP_TIMEOUT_SECONDS) as client:
            await client.post(
                self._url(TELEGRAM_METHOD_EDIT_TEXT),
                json={
                    FIELD_CHAT_ID: self._chat_id,
                    FIELD_MESSAGE_ID: message_id,
                    FIELD_TEXT: text,
                },
            )

    async def tell(self, text: str) -> None:
        """A plain owner message (published / failed notices)."""
        if not self.configured:
            return
        async with httpx.AsyncClient(timeout=TELEGRAM_HTTP_TIMEOUT_SECONDS) as client:
            await client.post(
                self._url(TELEGRAM_METHOD_MESSAGE),
                json={FIELD_CHAT_ID: self._chat_id, FIELD_TEXT: text},
            )

    async def _photo(self, client: httpx.AsyncClient, path: Path) -> None:
        await client.post(
            self._url(TELEGRAM_METHOD_PHOTO),
            data={FIELD_CHAT_ID: self._chat_id, FIELD_CAPTION: TEXT_COVER_CAPTION},
            files=cover_photo_file(str(path)),
        )

    async def _video(self, client: httpx.AsyncClient, path: Path) -> None:
        files = {TELEGRAM_FIELD_VIDEO: (path.name, path.read_bytes(), MEDIA_TYPE_MP4)}
        await client.post(
            self._url(TELEGRAM_METHOD_VIDEO),
            data={
                FIELD_CHAT_ID: self._chat_id,
                FIELD_CAPTION: TEXT_PREVIEW_CAPTION,
                TELEGRAM_FIELD_SUPPORTS_STREAMING: _TRUE,
            },
            files=files,
        )

    async def _prompt(
        self, client: httpx.AsyncClient, message: PreviewMessage
    ) -> int | None:
        response = await client.post(
            self._url(TELEGRAM_METHOD_MESSAGE),
            json={
                FIELD_CHAT_ID: self._chat_id,
                FIELD_TEXT: message.text,
                FIELD_REPLY_MARKUP: inline_markup(message.keyboard),
            },
        )
        if not response.is_success:
            return None
        try:
            return one_id(response.json())
        except (ValueError, KeyError, TypeError):
            return None

    def _url(self, method: str) -> str:
        return f"{TELEGRAM_API_HOST}/bot{self._token}/{method}"


__all__ = ["PreviewMessage", "TelegramRepostMessenger", "fits_telegram"]
