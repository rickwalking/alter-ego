"""Pure parsing of the Grok Bot callback body (AE-0393, contract section 2.2).

Success is the OpenAI ``ImagesResponse`` shape; only ``data[0].b64_json`` is
read (no ``url``: the bridge never fetches anything). Failure is the OpenAI
error shape. Anything else raises ``MalformedCallbackError``.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass

from rag_backend.modules.image_bridge.constants import (
    ERR_IMAGE_NOT_BASE64,
    ERR_IMAGE_TOO_LARGE,
    ERR_MALFORMED_DATA,
    ERR_MALFORMED_ENTRY,
    ERR_MALFORMED_ERROR,
    ERR_MALFORMED_NOT_OBJECT,
    ERROR_CODE_LENGTH,
    ERROR_CODE_UNKNOWN,
    ERROR_MESSAGE_MAX_CHARS,
    FIELD_B64_JSON,
    FIELD_CODE,
    FIELD_DATA,
    FIELD_ERROR,
    FIELD_MESSAGE,
    FIELD_TYPE,
    MAX_B64_CHARS,
    MAX_IMAGE_BYTES,
)
from rag_backend.modules.image_bridge.domain.exceptions import (
    InvalidCallbackImageError,
    MalformedCallbackError,
)


@dataclass(frozen=True)
class CallbackImage:
    """A success callback: the base64 image of ``data[0]``."""

    b64_json: str


@dataclass(frozen=True)
class CallbackError:
    """An error callback, e.g. a refusal."""

    code: str
    message: str


def parse_callback(payload: object) -> CallbackImage | CallbackError:
    """Classify a decoded JSON body, or raise ``MalformedCallbackError``."""
    if not isinstance(payload, dict):
        raise MalformedCallbackError(ERR_MALFORMED_NOT_OBJECT)
    if FIELD_ERROR in payload:
        return _parse_error(payload[FIELD_ERROR])
    return _parse_image(payload.get(FIELD_DATA))


def decode_image_b64(b64_json: str) -> bytes:
    """Strictly decode the base64 image, bounded by the decoded size limit."""
    compact = "".join(b64_json.split())
    if len(compact) > MAX_B64_CHARS:
        raise InvalidCallbackImageError(ERR_IMAGE_TOO_LARGE)
    try:
        image = base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidCallbackImageError(ERR_IMAGE_NOT_BASE64) from exc
    if len(image) > MAX_IMAGE_BYTES:
        raise InvalidCallbackImageError(ERR_IMAGE_TOO_LARGE)
    return image


def _parse_error(raw: object) -> CallbackError:
    if not isinstance(raw, dict):
        raise MalformedCallbackError(ERR_MALFORMED_ERROR)
    code = _text(raw.get(FIELD_CODE)) or _text(raw.get(FIELD_TYPE))
    message = _text(raw.get(FIELD_MESSAGE))
    return CallbackError(
        code=(code or ERROR_CODE_UNKNOWN)[:ERROR_CODE_LENGTH],
        message=message[:ERROR_MESSAGE_MAX_CHARS],
    )


def _parse_image(raw: object) -> CallbackImage:
    if not isinstance(raw, list) or not raw:
        raise MalformedCallbackError(ERR_MALFORMED_DATA)
    entry = raw[0]
    b64 = entry.get(FIELD_B64_JSON) if isinstance(entry, dict) else None
    if not isinstance(b64, str) or not b64.strip():
        raise MalformedCallbackError(ERR_MALFORMED_ENTRY)
    return CallbackImage(b64_json=b64)


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
