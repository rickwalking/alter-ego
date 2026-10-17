"""``Notifier`` adapter. Slide JPEGs are multipart uploads, never public URLs."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass

import httpx
import structlog

from rag_backend.modules.autopilot.cover_constants import (
    LOG_COVER,
    LOG_COVER_PHOTO_FAILED,
)
from rag_backend.modules.autopilot.domain.carousel_defaults import with_profile
from rag_backend.modules.autopilot.domain.cover_offer import (
    cover_caption,
    with_cover_row,
)
from rag_backend.modules.autopilot.domain.exceptions import (
    NotifierUnconfiguredError,
    TelegramDeliveryError,
    TelegramRateLimitedError,
)
from rag_backend.modules.autopilot.domain.messages import (
    ScoreSummary,
    album_caption,
    caption_preview,
)
from rag_backend.modules.autopilot.domain.notify import (
    ReviewNotice,
    ReviewSendResult,
    StatusNotice,
    StatusSendResult,
)
from rag_backend.modules.autopilot.domain.ports import Sleeper
from rag_backend.modules.autopilot.domain.review_issues import (
    review_keyboard_with_fix,
    with_issues,
)
from rag_backend.modules.autopilot.infrastructure.telegram_payload import (
    accepted_payload,
    cover_photo_file,
    group_ids,
    media_parts,
    message_data,
    one_id,
    photo_data,
    photo_file,
    retry_after_seconds,
)
from rag_backend.modules.autopilot.notify_constants import (
    DETAIL_RATE_LIMITED,
    DETAIL_TRANSPORT,
    FIELD_CAPTION,
    FIELD_CHAT_ID,
    FIELD_MEDIA,
    LOG_NOTIFIER_UNCONFIGURED,
    TELEGRAM_ALBUM_MIN,
    TELEGRAM_API_HOST,
    TELEGRAM_HTTP_TIMEOUT_SECONDS,
    TELEGRAM_METHOD_MEDIA_GROUP,
    TELEGRAM_METHOD_MESSAGE,
    TELEGRAM_METHOD_PHOTO,
    TELEGRAM_RATE_LIMIT_TRIES,
    TELEGRAM_RETRY_AFTER_CAP_SECONDS,
    TELEGRAM_STATUS_RATE_LIMITED,
)

logger = structlog.get_logger()

_File = tuple[str, bytes, str]


@dataclass(frozen=True, kw_only=True)
class TelegramClientConfig:
    """Token and the delay used when Telegram answers 429."""

    token: str
    sleeper: Sleeper
    client: httpx.AsyncClient | None = None


class AsyncSleeper:
    """Production delay. Tests inject a recorder instead."""

    def __init__(self) -> None:
        self._scale = 1.0

    async def sleep(self, seconds: float) -> None:
        """Wait ``seconds`` scaled by the instance factor."""
        await asyncio.sleep(seconds * self._scale)


class TelegramNotifier:
    """Bot API client for review albums and status messages."""

    def __init__(self, config: TelegramClientConfig) -> None:
        self._token = config.token.strip()
        self._sleeper = config.sleeper
        self._client = config.client or httpx.AsyncClient(
            timeout=TELEGRAM_HTTP_TIMEOUT_SECONDS
        )

    async def send_review(self, notice: ReviewNotice) -> ReviewSendResult:
        """Upload the album when it is not already stored, then the keyboard."""
        self._require_token()
        album_ids = notice.prior_album_ids or await self._album(notice)
        if not notice.prior_album_ids:
            await self._cover_preview(notice)
        keyboard_id = await self._keyboard_message(notice)
        return ReviewSendResult(album_ids=album_ids, keyboard_id=keyboard_id)

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        """Send one text message (AE-0418: or photo) and return its id."""
        self._require_token()
        if notice.photo_path:
            payload = await self._status_photo(notice, notice.photo_path)
        else:
            payload = await self._message(notice)
        return StatusSendResult(message_id=one_id(payload))

    def _require_token(self) -> None:
        if self._token:
            return
        logger.info(LOG_NOTIFIER_UNCONFIGURED)
        raise NotifierUnconfiguredError(LOG_NOTIFIER_UNCONFIGURED)

    async def _album(self, notice: ReviewNotice) -> tuple[int, ...]:
        caption = album_caption(_summary(notice))
        count = len(notice.slide_paths)
        if count >= TELEGRAM_ALBUM_MIN:
            payload = await self._group(notice.chat_id, notice.slide_paths, caption)
            return group_ids(payload)
        if count == 1:
            payload = await self._photo(notice.chat_id, notice.slide_paths[0], caption)
            return (one_id(payload),)
        return ()

    async def _keyboard_message(self, notice: ReviewNotice) -> int:
        status = StatusNotice(
            chat_id=notice.chat_id,
            run_id=notice.run_id,
            text=with_issues(
                with_profile(notice.profile, caption_preview(notice.caption)),
                notice.issues,
            ),
            keyboard=with_cover_row(
                review_keyboard_with_fix(notice.run_id, fixable=notice.fixable),
                notice.run_id,
                notice.cover,
            ),
        )
        payload = await self._message(status)
        return one_id(payload)

    async def _group(
        self,
        chat_id: str,
        paths: tuple[str, ...],
        caption: str,
    ) -> object:
        files, media = media_parts(paths, caption)
        data = {FIELD_CHAT_ID: chat_id, FIELD_MEDIA: json.dumps(media)}
        return await self._post(TELEGRAM_METHOD_MEDIA_GROUP, data, files)

    async def _photo(self, chat_id: str, path: str, caption: str) -> object:
        files = photo_file(path)
        data = {FIELD_CHAT_ID: chat_id, FIELD_CAPTION: caption}
        return await self._post(TELEGRAM_METHOD_PHOTO, data, files)

    async def _status_photo(self, notice: StatusNotice, path: str) -> object:
        data = photo_data(notice.chat_id, notice.text, notice.keyboard)
        return await self._post(TELEGRAM_METHOD_PHOTO, data, cover_photo_file(path))

    async def _cover_preview(self, notice: ReviewNotice) -> None:
        """AE-0418: the GrokBot cover after the album, while it is not slide 1.

        A failed preview is logged; it never blocks the review itself.
        """
        cover = notice.cover
        if cover is None or cover.chosen:
            return
        data = photo_data(notice.chat_id, cover_caption(cover), None)
        try:
            await self._post(
                TELEGRAM_METHOD_PHOTO, data, cover_photo_file(cover.photo_path)
            )
        except (TelegramDeliveryError, OSError, ValueError) as exc:
            logger.warning(
                LOG_COVER, outcome=LOG_COVER_PHOTO_FAILED, error=type(exc).__name__
            )

    async def _message(self, notice: StatusNotice) -> object:
        data = message_data(notice.chat_id, notice.text, notice.keyboard)
        return await self._post(TELEGRAM_METHOD_MESSAGE, data, {})

    async def _post(
        self,
        method: str,
        data: dict[str, str],
        files: Mapping[str, _File],
    ) -> object:
        url = f"{TELEGRAM_API_HOST}/bot{self._token}/{method}"
        attempt = 0
        while True:
            response = await self._request(url, data, files)
            if response.status_code != TELEGRAM_STATUS_RATE_LIMITED:
                return accepted_payload(response)
            if attempt >= TELEGRAM_RATE_LIMIT_TRIES:
                raise TelegramRateLimitedError(DETAIL_RATE_LIMITED)
            await self._wait(response)
            attempt += 1

    async def _request(
        self,
        url: str,
        data: dict[str, str],
        files: Mapping[str, _File],
    ) -> httpx.Response:
        try:
            if files:
                return await self._client.post(url, data=data, files=dict(files))
            return await self._client.post(url, data=data)
        except httpx.HTTPError:
            raise TelegramDeliveryError(DETAIL_TRANSPORT) from None

    async def _wait(self, response: httpx.Response) -> None:
        seconds = retry_after_seconds(response)
        if seconds > TELEGRAM_RETRY_AFTER_CAP_SECONDS:
            raise TelegramRateLimitedError(DETAIL_RATE_LIMITED)
        await self._sleeper.sleep(seconds)


def _summary(notice: ReviewNotice) -> ScoreSummary:
    return ScoreSummary(
        title=notice.title,
        persona_score=notice.persona_score,
        sources_count=notice.sources_count,
    )
