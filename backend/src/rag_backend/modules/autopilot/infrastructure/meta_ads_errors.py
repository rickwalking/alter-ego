"""Marketing API errors: a stable code plus Meta's own fields, never a secret."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from rag_backend.modules.autopilot.boost_constants import HTTP_ERROR_MIN
from rag_backend.modules.autopilot.meta_ads_constants import (
    CALL_PREFLIGHT_MEDIA,
    DETAIL_MAX_CHARS,
    ERR_APP_DEV_MODE,
    ERR_MEDIA_UNREADABLE,
    ERR_META_BAD_BODY,
    ERR_META_TRANSIENT,
    ERR_PREFIX_META,
    FIELD_CALL,
    FIELD_CODE,
    FIELD_HTTP_STATUS,
    FIELD_SUBCODE,
    META_CODE_PARAM,
    META_ERROR_FIELDS,
    META_SUBCODE_APP_DEV_MODE,
    META_SUBCODE_UNSUPPORTED_GET,
    REDACTED,
)


class AdsCallError(Exception):
    """A classified Marketing API failure. Permanent errors do not retry.

    ``detail`` holds which call failed and Meta's error fields as strings, ready for
    the failure event and the log. It never holds the token or the appsecret proof.
    """

    def __init__(
        self,
        code: str,
        *,
        permanent: bool,
        detail: dict[str, str] | None = None,
    ) -> None:
        self.code = code
        self.permanent = permanent
        self.detail: dict[str, str] = dict(detail or {})
        super().__init__(code)


@dataclass(frozen=True, kw_only=True)
class CallContext:
    """Which call this was, and the secrets to scrub from anything Meta echoes."""

    call: str
    secrets: tuple[str, ...]


def read_body(response: httpx.Response, context: CallContext) -> dict[str, object]:
    """The JSON body of a success, else an ``AdsCallError`` with Meta's details."""
    body = _parsed(response)
    if response.is_success and body is not None:
        return body
    detail = _detail(response, body, context)
    if response.status_code >= HTTP_ERROR_MIN:
        raise AdsCallError(ERR_META_TRANSIENT, permanent=False, detail=detail)
    if body is None:
        code = ERR_META_TRANSIENT if _not_json(response) else ERR_META_BAD_BODY
        raise AdsCallError(code, permanent=code == ERR_META_BAD_BODY, detail=detail)
    raise AdsCallError(_code(detail, response), permanent=True, detail=detail)


def _parsed(response: httpx.Response) -> dict[str, object] | None:
    try:
        body = response.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def _not_json(response: httpx.Response) -> bool:
    try:
        response.json()
    except ValueError:
        return True
    return False


def _detail(
    response: httpx.Response, body: dict[str, object] | None, context: CallContext
) -> dict[str, str]:
    detail = {FIELD_CALL: context.call, FIELD_HTTP_STATUS: str(response.status_code)}
    error = body.get("error") if body is not None else None
    if not isinstance(error, dict):
        return detail
    for name in META_ERROR_FIELDS:
        value = error.get(name)
        if value is None or isinstance(value, (dict, list)):
            continue
        detail[name] = _scrub(str(value), context.secrets)
    return detail


def _scrub(text: str, secrets: tuple[str, ...]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, REDACTED)
    return text[:DETAIL_MAX_CHARS]


def _code(detail: dict[str, str], response: httpx.Response) -> str:
    code = detail.get(FIELD_CODE, str(response.status_code))
    subcode = detail.get(FIELD_SUBCODE, "")
    if subcode == str(META_SUBCODE_APP_DEV_MODE):
        return ERR_APP_DEV_MODE
    media_call = detail.get(FIELD_CALL) == CALL_PREFLIGHT_MEDIA
    unreadable = (code, subcode) == (
        str(META_CODE_PARAM),
        str(META_SUBCODE_UNSUPPORTED_GET),
    )
    if media_call and unreadable:
        return ERR_MEDIA_UNREADABLE
    return f"{ERR_PREFIX_META}{code}"


__all__ = ["AdsCallError", "CallContext", "read_body"]
