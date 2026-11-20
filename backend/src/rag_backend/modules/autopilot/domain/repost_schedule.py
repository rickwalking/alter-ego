"""When an approved repost goes out: the best slot inside its window. Pure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from rag_backend.modules.autopilot.domain.recommend import (
    RecommendQuery,
    ScheduleSignals,
    ScoredSlot,
    slots_on,
)
from rag_backend.modules.autopilot.domain.repost import PublishWindow
from rag_backend.modules.autopilot.domain.schedule import schedule_zone


@dataclass(frozen=True, kw_only=True)
class PublishTimeQuery:
    """The draft's window, the approval time and the account's signals."""

    window: PublishWindow | None
    now: datetime
    signals: ScheduleSignals


def publish_time(query: PublishTimeQuery) -> datetime:
    """The best-scored slot inside the window; else its start; else now."""
    window = query.window
    if window is None:
        return query.now
    start = max(query.now, window.earliest)
    if start >= window.latest:
        return query.now
    slots = _slots(query, start, window.latest)
    if not slots:
        return start
    return min(slots, key=lambda slot: (-slot.score, slot.at)).at


def _slots(query: PublishTimeQuery, start: datetime, end: datetime) -> list[ScoredSlot]:
    recommend = RecommendQuery(now=query.now, pov=False, signals=query.signals)
    zone = schedule_zone()
    day = start.astimezone(zone).date()
    last = end.astimezone(zone).date()
    found: list[ScoredSlot] = []
    while day <= last:
        found.extend(s for s in slots_on(recommend, day) if start <= s.at <= end)
        day += timedelta(days=1)
    return found


__all__ = ["PublishTimeQuery", "publish_time"]
