"""Pure text and time rules for topic intake.

No I/O. The service loads facts and ``intake.plan_intake`` applies these
checks. Control characters are removed before hashing and URL detection so
a null byte cannot hide a link.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from rag_backend.modules.autopilot.constants import (
    DAILY_CAP_TIMEZONE,
    HASH_FIELD_SEPARATOR,
    JACCARD_DUPLICATE_THRESHOLD,
    SERVED_URL_TTL_HOURS,
    SOURCE_URL_PATTERN,
    TEXT_ENCODING,
    TOPIC_LOOKBACK_DAYS,
    UNICODE_CATEGORY_CONTROL,
    URL_IN_TEXT_PATTERN,
    WORD_PATTERN,
)
from rag_backend.modules.autopilot.domain.x_status import canonical_url

_URL_IN_TEXT = re.compile(URL_IN_TEXT_PATTERN)
_SOURCE_URL = re.compile(SOURCE_URL_PATTERN)
_TOKEN = re.compile(WORD_PATTERN, re.UNICODE)


def strip_controls(value: str) -> str:
    """Drop Unicode control characters and surrounding whitespace."""
    kept = "".join(
        ch for ch in value if unicodedata.category(ch) != UNICODE_CATEGORY_CONTROL
    )
    return kept.strip()


def contains_url(value: str) -> bool:
    """True when free text contains a URL or a ``www.`` host."""
    return _URL_IN_TEXT.search(value) is not None


def is_http_url(value: str) -> bool:
    """True when ``value`` is an http or https URL without spaces."""
    return _SOURCE_URL.fullmatch(value) is not None


def normalize_title(title: str) -> str:
    """Casefold and collapse whitespace for the signal hash."""
    return " ".join(title.casefold().split())


def signal_hash(title: str, sources: tuple[str, ...]) -> str:
    """sha256 of the normalized title plus the sorted canonical sources."""
    canonical = tuple(sorted(canonical_url(source) for source in sources))
    material = HASH_FIELD_SEPARATOR.join((normalize_title(title), *canonical))
    digest = hashlib.sha256(material.encode(TEXT_ENCODING))
    return digest.hexdigest()


def tokens(title: str) -> frozenset[str]:
    """Unicode word tokens of a casefolded title. Underscores are dropped."""
    return frozenset(_TOKEN.findall(title.casefold()))


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    """Token Jaccard. An empty side scores 0 so a blank title is not a duplicate."""
    if not left or not right:
        return 0.0
    shared = len(left & right)
    union = len(left | right)
    return shared / union


def titles_are_duplicates(left: str, right: str) -> bool:
    """True when token Jaccard is at least the duplicate threshold (0.6)."""
    return jaccard(tokens(left), tokens(right)) >= JACCARD_DUPLICATE_THRESHOLD


def as_utc(moment: datetime) -> datetime:
    """Attach UTC when ``moment`` is naive. Aware values are unchanged."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment


def served_url_cutoff(moment: datetime) -> datetime:
    """Instants at or after this cutoff were served within the last 6 hours."""
    return as_utc(moment) - timedelta(hours=SERVED_URL_TTL_HOURS)


def carousel_topic_cutoff(moment: datetime) -> datetime:
    """Carousel topics created at or after this cutoff are inside 60 days."""
    return as_utc(moment) - timedelta(days=TOPIC_LOOKBACK_DAYS)


def sao_paulo_day(moment: datetime) -> tuple[datetime, datetime]:
    """UTC bounds of the America/Sao_Paulo calendar day containing ``moment``.

    The end is exclusive. A run at 23:30 local time stays on that local day.
    """
    local = as_utc(moment).astimezone(ZoneInfo(DAILY_CAP_TIMEZONE))
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    start = start_local.astimezone(UTC)
    return start, start + timedelta(days=1)
