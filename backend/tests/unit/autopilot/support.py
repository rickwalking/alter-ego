"""Shared builders for autopilot signal tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from rag_backend.modules.autopilot.constants import TWITTER_SNOWFLAKE_EPOCH_MS
from rag_backend.modules.autopilot.domain.signals import (
    CollectWindow,
    Signal,
    SignalDraft,
    SignalSource,
    signal_from,
)

AS_OF = datetime(2026, 10, 13, 15, 0, tzinfo=UTC)
WINDOW = CollectWindow(as_of=AS_OF)


def snowflake_id(moment: datetime) -> str:
    """Status id whose snowflake time is ``moment`` (millisecond precision)."""
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    delta = moment - epoch
    millis = (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000
    return str((millis - TWITTER_SNOWFLAKE_EPOCH_MS) << 22)


def make_signal(
    source: SignalSource,
    url: str,
    *,
    title: str = "Title",
    text: str = "Text",
    posted_at: datetime | None = None,
) -> Signal:
    """A signal that passes ``signal_from``. Tests fail loudly if it does not."""
    built = signal_from(
        SignalDraft(
            source=source,
            url=url,
            title=title,
            text=text,
            posted_at=posted_at or AS_OF,
        )
    )
    assert built is not None
    return built


def hours_before(hours: int) -> datetime:
    """``AS_OF`` minus ``hours``."""
    return AS_OF - timedelta(hours=hours)
