"""Typed trend signals returned to the scout.

``Signal`` is the collector contract (AE-0352). ``source`` is one of the
free backends in architecture §5. Ranking is out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from rag_backend.modules.autopilot.constants import (
    MAX_SIGNAL_TEXT_CHARS,
    SOURCE_BLUESKY,
    SOURCE_GITHUB,
    SOURCE_HF_PAPERS,
    SOURCE_HN,
    SOURCE_RSS,
    SOURCE_X_SEARCH,
)


class SignalSource(StrEnum):
    """Free backends the bundle is allowed to name."""

    X_SEARCH = SOURCE_X_SEARCH
    HN = SOURCE_HN
    HF_PAPERS = SOURCE_HF_PAPERS
    RSS = SOURCE_RSS
    BLUESKY = SOURCE_BLUESKY
    GITHUB = SOURCE_GITHUB


@dataclass(frozen=True, kw_only=True)
class Signal:
    """One deduped trend item. ``handle`` and ``score_hint`` are optional."""

    source: SignalSource
    url: str
    title: str
    text: str
    posted_at: datetime
    handle: str | None = None
    score_hint: int | None = None


@dataclass(frozen=True, kw_only=True)
class CollectorError:
    """A collector that timed out or raised. The bundle still returns."""

    source: str
    message: str


@dataclass(frozen=True, kw_only=True)
class SignalsBundle:
    """Body of ``GET /api/autopilot/signals``."""

    generated_at: datetime
    signals: list[Signal]
    errors: list[CollectorError]


@dataclass(frozen=True, kw_only=True)
class CollectWindow:
    """Reference instant for one scout run. Collectors derive cutoffs from it."""

    as_of: datetime


@dataclass(frozen=True, kw_only=True)
class SignalDraft:
    """Fields a collector has gathered before validation."""

    source: SignalSource
    url: str
    title: str
    text: str
    posted_at: datetime
    handle: str | None = None
    score_hint: int | None = None


def ensure_utc(value: datetime) -> datetime:
    """Return ``value`` as an aware UTC datetime."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def clip_text(value: str) -> str:
    """Trim surrounding space and cap the length stored on a signal."""
    trimmed = value.strip()
    if len(trimmed) <= MAX_SIGNAL_TEXT_CHARS:
        return trimmed
    return trimmed[:MAX_SIGNAL_TEXT_CHARS]


def signal_from(draft: SignalDraft) -> Signal | None:
    """Build a signal, or None when the URL or the copy is missing."""
    url = draft.url.strip()
    title = clip_text(draft.title)
    text = clip_text(draft.text)
    if not url or not (title or text):
        return None
    return Signal(
        source=draft.source,
        url=url,
        title=title,
        text=text,
        posted_at=ensure_utc(draft.posted_at),
        handle=draft.handle,
        score_hint=draft.score_hint,
    )
