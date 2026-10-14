"""Telegram request bodies and response ids. No network."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from rag_backend.modules.autopilot.domain.exceptions import TelegramDeliveryError
from rag_backend.modules.autopilot.domain.messages import InlineButton, InlineKeyboard
from rag_backend.modules.autopilot.notify_constants import (
    ATTACH_SCHEME,
    DETAIL_BAD_RESPONSE,
    DETAIL_HTTP_STATUS,
    DETAIL_NOT_OK,
    FIELD_CALLBACK_DATA,
    FIELD_CAPTION,
    FIELD_CHAT_ID,
    FIELD_INLINE_KEYBOARD,
    FIELD_MEDIA,
    FIELD_MESSAGE_ID,
    FIELD_OK,
    FIELD_PARAMETERS,
    FIELD_REPLY_MARKUP,
    FIELD_RESULT,
    FIELD_RETRY_AFTER,
    FIELD_TEXT,
    FIELD_TYPE,
    FILE_FIELD_PREFIX,
    MEDIA_TYPE_PHOTO,
    TELEGRAM_PHOTO_MIME,
    TELEGRAM_RETRY_AFTER_DEFAULT,
)

_File = tuple[str, bytes, str]


def media_parts(
    paths: tuple[str, ...],
    caption: str,
) -> tuple[dict[str, _File], list[dict[str, str]]]:
    """Multipart bytes plus the ``media`` JSON. Bytes can be retried after 429."""
    files: dict[str, _File] = {}
    media: list[dict[str, str]] = []
    for index, path in enumerate(paths):
        field = f"{FILE_FIELD_PREFIX}{index}"
        files[field] = _jpeg(path)
        item = {FIELD_TYPE: MEDIA_TYPE_PHOTO, FIELD_MEDIA: f"{ATTACH_SCHEME}{field}"}
        if index == 0:
            item[FIELD_CAPTION] = caption
        media.append(item)
    return files, media


def photo_file(path: str) -> dict[str, _File]:
    """One JPEG part named ``photo``."""
    return {MEDIA_TYPE_PHOTO: _jpeg(path)}


def _jpeg(path: str) -> _File:
    file = Path(path)
    return (file.name, file.read_bytes(), TELEGRAM_PHOTO_MIME)


def markup(keyboard: InlineKeyboard) -> dict[str, object]:
    """``reply_markup`` object for ``sendMessage``."""
    rows = [[_button(button) for button in row] for row in keyboard.rows]
    return {FIELD_INLINE_KEYBOARD: rows}


def message_data(
    chat_id: str,
    text: str,
    keyboard: InlineKeyboard | None,
) -> dict[str, str]:
    """Form fields for ``sendMessage``."""
    data = {FIELD_CHAT_ID: chat_id, FIELD_TEXT: text}
    if keyboard is not None:
        data[FIELD_REPLY_MARKUP] = json.dumps(markup(keyboard))
    return data


def accepted_payload(response: httpx.Response) -> object:
    """JSON body of a successful call, or a token-free error."""
    if not response.is_success:
        detail = DETAIL_HTTP_STATUS.format(status=response.status_code)
        raise TelegramDeliveryError(detail)
    payload = _json(response)
    if isinstance(payload, dict) and payload.get(FIELD_OK) is False:
        raise TelegramDeliveryError(DETAIL_NOT_OK)
    return payload


def group_ids(payload: object) -> tuple[int, ...]:
    """Message ids from a ``sendMediaGroup`` result list."""
    result = _result(payload)
    if not isinstance(result, list) or not result:
        raise TelegramDeliveryError(DETAIL_BAD_RESPONSE)
    return tuple(_message_id(item) for item in result)


def one_id(payload: object) -> int:
    """Message id from a single ``sendMessage`` or ``sendPhoto`` result."""
    result = _result(payload)
    return _message_id(result)


def retry_after_seconds(response: httpx.Response) -> float:
    """``parameters.retry_after``, or the default when the body omits it."""
    payload = _json(response)
    if not isinstance(payload, dict):
        return TELEGRAM_RETRY_AFTER_DEFAULT
    params = payload.get(FIELD_PARAMETERS)
    if not isinstance(params, dict):
        return TELEGRAM_RETRY_AFTER_DEFAULT
    value = params.get(FIELD_RETRY_AFTER)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return TELEGRAM_RETRY_AFTER_DEFAULT
    return float(value)


def _button(button: InlineButton) -> dict[str, str]:
    return {FIELD_TEXT: button.text, FIELD_CALLBACK_DATA: button.callback_data}


def _result(payload: object) -> object:
    if not isinstance(payload, dict):
        raise TelegramDeliveryError(DETAIL_BAD_RESPONSE)
    return payload.get(FIELD_RESULT)


def _message_id(item: object) -> int:
    if not isinstance(item, dict):
        raise TelegramDeliveryError(DETAIL_BAD_RESPONSE)
    value = item.get(FIELD_MESSAGE_ID)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TelegramDeliveryError(DETAIL_BAD_RESPONSE)
    return value


def _json(response: httpx.Response) -> object:
    try:
        body: object = response.json()
    except ValueError:
        return {}
    return body
