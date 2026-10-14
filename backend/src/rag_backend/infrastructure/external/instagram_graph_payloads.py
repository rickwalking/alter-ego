"""Pure parsers for Instagram Graph response bodies. No HTTP calls.

``quota_remaining`` reads ``content_publishing_limit``. ``recent_carousel_id``
recovers the media id of a container that is already ``PUBLISHED`` (QA r1 H2):
the container node does not link to its media, so the one carousel album
posted after the container was created is taken as the one it produced
(QA r2 R3). A manual post from before the container is never matched, and
two albums after it are ambiguous: nothing is guessed, and the caller fails
the publish without retrying.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import httpx

from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_QUOTA_UNREADABLE,
    FIELD_ID,
    FIELD_MEDIA_TYPE,
    FIELD_TIMESTAMP,
    GRAPH_TIMESTAMP_FORMAT,
    KEY_CODE,
    KEY_CONFIG,
    KEY_DATA,
    KEY_ERROR,
    KEY_QUOTA_TOTAL,
    KEY_QUOTA_USAGE,
    MEDIA_TYPE_CAROUSEL_ALBUM,
    TRANSIENT_HTTP_STATUS,
    TRANSIENT_META_ERROR_CODES,
)
from rag_backend.infrastructure.external.instagram_graph_error import (
    InstagramGraphError,
)


@dataclass(frozen=True, kw_only=True)
class RecentMedia:
    """One carousel album from ``/{ig_user_id}/media``."""

    media_id: str
    posted_at: datetime


def quota_remaining(payload: dict[str, object]) -> int:
    """``quota_total - quota_usage``. Unreadable bodies raise a transient error."""
    data = payload.get(KEY_DATA)
    if not isinstance(data, list) or not data:
        raise quota_error()
    first = data[0]
    if not isinstance(first, dict):
        raise quota_error()
    usage = first.get(KEY_QUOTA_USAGE)
    config = first.get(KEY_CONFIG)
    if isinstance(usage, bool) or not isinstance(usage, int):
        raise quota_error()
    if not isinstance(config, dict):
        raise quota_error()
    total = config.get(KEY_QUOTA_TOTAL)
    if isinstance(total, bool) or not isinstance(total, int):
        raise quota_error()
    return total - usage


def quota_error() -> InstagramGraphError:
    """Transient: the next tick reads the limit again."""
    return InstagramGraphError(
        status_code=200,
        error_code=ERR_INSTAGRAM_QUOTA_UNREADABLE,
        transient=True,
    )


def recent_carousel_id(payload: dict[str, object], since: datetime) -> str | None:
    """The only carousel album posted at or after ``since``, or None."""
    albums = [item for item in _albums(payload) if item.posted_at >= since]
    if len(albums) != 1:
        return None
    return albums[0].media_id


def _albums(payload: dict[str, object]) -> list[RecentMedia]:
    data = payload.get(KEY_DATA)
    if not isinstance(data, list):
        return []
    parsed = [_album(item) for item in data]
    return [item for item in parsed if item is not None]


def _album(item: object) -> RecentMedia | None:
    if not isinstance(item, dict):
        return None
    if item.get(FIELD_MEDIA_TYPE) != MEDIA_TYPE_CAROUSEL_ALBUM:
        return None
    media_id = item.get(FIELD_ID)
    posted_at = _timestamp(item.get(FIELD_TIMESTAMP))
    if not isinstance(media_id, str) or not media_id or posted_at is None:
        return None
    return RecentMedia(media_id=media_id, posted_at=posted_at)


def _timestamp(raw: object) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        return datetime.strptime(raw, GRAPH_TIMESTAMP_FORMAT)
    except ValueError:
        return None


def json_dict(response: httpx.Response) -> dict[str, object]:
    """Response body as a string-keyed dict. Non-objects become empty."""
    body: object = response.json()
    if not isinstance(body, dict):
        return {}
    return {str(key): value for key, value in body.items()}


def error_from(response: httpx.Response) -> InstagramGraphError:
    """Graph error with the Meta code; 429/5xx and rate-limit codes are transient."""
    code = meta_code(response)
    transient = (
        response.status_code in TRANSIENT_HTTP_STATUS
        or code in TRANSIENT_META_ERROR_CODES
    )
    return InstagramGraphError(
        status_code=response.status_code,
        error_code=code,
        transient=transient,
    )


def meta_code(response: httpx.Response) -> str:
    """Meta ``error.code``, or the HTTP status when the body has none."""
    error = json_dict(response).get(KEY_ERROR)
    if isinstance(error, dict):
        code = error.get(KEY_CODE)
        if code is not None:
            return str(code)
    return str(response.status_code)
