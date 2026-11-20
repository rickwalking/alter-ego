"""Parse the ``GET /reels`` query and its opaque cursor. No I/O."""

from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.modules.autopilot.domain.repost import invalid
from rag_backend.modules.autopilot.reels_constants import (
    CURSOR_MAX_OFFSET,
    CURSOR_PREFIX,
    DEFAULT_EXCLUDE_DAYS,
    DEFAULT_LIMIT,
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_MIN_AGE_DAYS,
    MAX_AGE_DAYS_CAP,
    MAX_LIMIT,
    MSG_AGE_ORDER,
    MSG_CURSOR,
    MSG_INTEGER,
    MSG_RANGE,
    MSG_SORT,
    MSG_UNKNOWN_PARAM,
    QUERY_CURSOR,
    QUERY_EXCLUDE,
    QUERY_LIMIT,
    QUERY_MAX_AGE,
    QUERY_MIN_AGE,
    QUERY_PARAMS,
    QUERY_SORT,
    SORT_VIEWS,
    SORTS,
)


@dataclass(frozen=True, kw_only=True)
class ReelsQuery:
    """A validated ``GET /reels`` query."""

    min_age_days: int = DEFAULT_MIN_AGE_DAYS
    max_age_days: int = DEFAULT_MAX_AGE_DAYS
    limit: int = DEFAULT_LIMIT
    offset: int = 0
    sort: str = SORT_VIEWS
    exclude_reposted_days: int = DEFAULT_EXCLUDE_DAYS


@dataclass(frozen=True, kw_only=True)
class _Bounds:
    name: str
    default: int
    low: int
    high: int


def parse_reels_query(params: Mapping[str, str]) -> ReelsQuery:
    """The query, or 400 ``invalid_field`` naming the bad parameter."""
    unknown = sorted(set(params) - QUERY_PARAMS)
    if unknown:
        raise invalid(unknown[0], MSG_UNKNOWN_PARAM)
    query = ReelsQuery(
        min_age_days=_int(
            params,
            _Bounds(
                name=QUERY_MIN_AGE,
                default=DEFAULT_MIN_AGE_DAYS,
                low=0,
                high=MAX_AGE_DAYS_CAP,
            ),
        ),
        max_age_days=_int(
            params,
            _Bounds(
                name=QUERY_MAX_AGE,
                default=DEFAULT_MAX_AGE_DAYS,
                low=1,
                high=MAX_AGE_DAYS_CAP,
            ),
        ),
        limit=_int(
            params,
            _Bounds(name=QUERY_LIMIT, default=DEFAULT_LIMIT, low=1, high=MAX_LIMIT),
        ),
        offset=decode_cursor(params.get(QUERY_CURSOR)),
        sort=_sort(params.get(QUERY_SORT)),
        exclude_reposted_days=_int(
            params,
            _Bounds(
                name=QUERY_EXCLUDE,
                default=DEFAULT_EXCLUDE_DAYS,
                low=0,
                high=MAX_AGE_DAYS_CAP,
            ),
        ),
    )
    if query.min_age_days > query.max_age_days:
        raise invalid(QUERY_MIN_AGE, MSG_AGE_ORDER)
    return query


def encode_cursor(offset: int) -> str:
    """An opaque cursor for the next page."""
    raw = f"{CURSOR_PREFIX}{offset}".encode(ENCODING_UTF8)
    return base64.urlsafe_b64encode(raw).decode(ENCODING_UTF8).rstrip("=")


def decode_cursor(value: str | None) -> int:
    """The offset inside a cursor; 0 without one."""
    if value is None or value == "":
        return 0
    padded = value + "=" * (-len(value) % 4)
    try:
        text = base64.urlsafe_b64decode(padded.encode(ENCODING_UTF8)).decode(
            ENCODING_UTF8
        )
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise invalid(QUERY_CURSOR, MSG_CURSOR) from None
    digits = text.removeprefix(CURSOR_PREFIX)
    if not text.startswith(CURSOR_PREFIX) or not digits.isdigit():
        raise invalid(QUERY_CURSOR, MSG_CURSOR)
    offset = int(digits)
    if offset > CURSOR_MAX_OFFSET:
        raise invalid(QUERY_CURSOR, MSG_CURSOR)
    return offset


def _int(params: Mapping[str, str], bounds: _Bounds) -> int:
    raw = params.get(bounds.name)
    if raw is None:
        return bounds.default
    if not raw.isdigit():
        raise invalid(bounds.name, MSG_INTEGER)
    value = int(raw)
    if not bounds.low <= value <= bounds.high:
        raise invalid(bounds.name, MSG_RANGE)
    return value


def _sort(raw: str | None) -> str:
    if raw is None:
        return SORT_VIEWS
    if raw not in SORTS:
        raise invalid(QUERY_SORT, MSG_SORT)
    return raw


__all__ = ["ReelsQuery", "decode_cursor", "encode_cursor", "parse_reels_query"]
