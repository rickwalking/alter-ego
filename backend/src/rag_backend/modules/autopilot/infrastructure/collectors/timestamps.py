"""Parse the timestamps the free signal APIs actually return."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

_ZULU_SUFFIX = "Z"
_ZULU_OFFSET = "+00:00"


def parse_timestamp(value: str) -> datetime | None:
    """Parse an ISO-8601 or RFC 822 timestamp as aware UTC."""
    text = value.strip()
    if not text:
        return None
    parsed = _from_iso(text)
    if parsed is None:
        parsed = _from_rfc822(text)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _from_iso(text: str) -> datetime | None:
    iso = text
    if text.endswith(_ZULU_SUFFIX):
        iso = text[:-1] + _ZULU_OFFSET
    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        return None


def _from_rfc822(text: str) -> datetime | None:
    try:
        return parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None
