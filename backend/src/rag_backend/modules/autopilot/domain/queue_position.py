"""One pure queue order and retry-aware position/ETA calculation."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from rag_backend.modules.autopilot.queue_constants import (
    DEFAULT_DRIVE_MINUTES,
    ELLIPSIS,
    ETA_FORMAT,
    GENERATION_STATUS_QUEUED,
    GENERATION_STATUS_RETRY_WAIT,
    GENERATION_STATUS_RUNNING,
    LIST_SEPARATOR,
    LIST_TITLE_MAX_CHARS,
    QUEUE_TIMEZONE,
    TEXT_QUEUE_POSITION,
)

_SECONDS_PER_MINUTE = 60.0
_LEGACY_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


@dataclass(frozen=True, kw_only=True)
class QueueEntry:
    """All transport and timing metadata needed to place one unit of work."""

    id: str
    status: str
    autopilot_run_id: str | None
    created_at: datetime
    pgq_job_id: int | None = None
    priority: int = 0
    started_at: datetime | None = None
    next_attempt_at: datetime | None = None
    staged: bool = True


@dataclass(frozen=True, kw_only=True)
class QueueSnapshot:
    """One queue snapshot; ``ahead`` and ``waiting`` retain the legacy adapter view."""

    entries: tuple[QueueEntry, ...] = ()
    drive_minutes: tuple[float, ...] = ()
    ahead: tuple[str | None, ...] = ()
    waiting: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class QueuePlacement:
    """One ordered entry, its visible position and its estimated start."""

    entry: QueueEntry
    position: int | None
    eta: datetime | None


@dataclass(frozen=True, kw_only=True)
class QueuePosition:
    """1-based position, queue length and estimated start."""

    position: int
    total: int
    eta: datetime


class QueueControl(Protocol):
    """The generation queue as the owner's Telegram actions see it."""

    async def snapshot(self) -> QueueSnapshot:
        """The current order, read in the caller's transaction."""
        ...

    async def requeue_dead_letter(self, run_id: UUID) -> bool:
        """Requeue the run's dead-lettered generation run; False when there is none."""
        ...

    async def reprocess_autopilot(self, run_id: UUID, actor_id: str) -> UUID | None:
        """Use shared manual recovery; return its queued autopilot identity."""
        ...


def average_drive_minutes(drives: Sequence[float]) -> float:
    """The mean of the recent drives, or the default without history."""
    if not drives:
        return float(DEFAULT_DRIVE_MINUTES)
    return sum(drives) / len(drives)


def queue_placements(
    snapshot: QueueSnapshot, now: datetime
) -> tuple[QueuePlacement, ...]:
    """Order every entry and schedule it with running and retry timing included."""
    entries = sorted(_entries(snapshot), key=_order_key)
    average = average_drive_minutes(snapshot.drive_minutes)
    running = next((entry for entry in entries if _running(entry)), None)
    available = _running_finish(running, now, average)
    return _schedule(entries, available, average)


def _schedule(
    entries: list[QueueEntry], available: datetime, average: float
) -> tuple[QueuePlacement, ...]:
    position = 0
    placements: list[QueuePlacement] = []
    for entry in entries:
        if _running(entry):
            position += 1
            placements.append(QueuePlacement(entry=entry, position=position, eta=None))
            continue
        start = _entry_start(entry, available)
        position += int(entry.status != GENERATION_STATUS_RETRY_WAIT)
        visible = position if entry.status != GENERATION_STATUS_RETRY_WAIT else None
        placements.append(QueuePlacement(entry=entry, position=visible, eta=start))
        available = start + timedelta(minutes=average)
    return tuple(placements)


def position_of(
    snapshot: QueueSnapshot, run_id: UUID, now: datetime
) -> QueuePosition | None:
    """The queued run's shared position and ETA; None when not visibly queued."""
    placements = queue_placements(snapshot, now)
    key = str(run_id)
    found = next(
        (
            place
            for place in placements
            if place.entry.autopilot_run_id == key and place.eta is not None
        ),
        None,
    )
    if found is None or found.position is None or found.eta is None:
        return None
    total = sum(place.position is not None for place in placements)
    return QueuePosition(position=found.position, total=total, eta=found.eta)


def position_text(position: QueuePosition) -> str:
    """``Na fila: posição N de M — início estimado HH:MM`` (São Paulo time)."""
    return TEXT_QUEUE_POSITION.format(
        position=position.position, total=position.total, eta=local_time(position.eta)
    )


def joined_titles(titles: Iterable[str]) -> str:
    """Titles joined for one message, each cut to ``LIST_TITLE_MAX_CHARS``."""
    return LIST_SEPARATOR.join(_short(title) for title in titles)


def local_time(moment: datetime) -> str:
    """``HH:MM`` in São Paulo time."""
    return moment.astimezone(ZoneInfo(QUEUE_TIMEZONE)).strftime(ETA_FORMAT)


def _entries(snapshot: QueueSnapshot) -> tuple[QueueEntry, ...]:
    if snapshot.entries:
        return snapshot.entries
    combined = [*snapshot.ahead, *snapshot.waiting]
    return tuple(
        _legacy_entry(f"legacy-{index}", run_id, index)
        for index, run_id in enumerate(combined)
    )


def _legacy_entry(entry_id: str, run_id: str | None, index: int) -> QueueEntry:
    return QueueEntry(
        id=entry_id,
        status=GENERATION_STATUS_QUEUED,
        autopilot_run_id=run_id,
        created_at=_LEGACY_EPOCH + timedelta(microseconds=index),
    )


def _order_key(entry: QueueEntry) -> tuple[int, int, int, int, datetime, str]:
    return (
        int(not _running(entry)),
        -entry.priority,
        int(entry.pgq_job_id is None),
        entry.pgq_job_id or 0,
        _aware(entry.created_at),
        entry.id,
    )


def _running(entry: QueueEntry) -> bool:
    return entry.status == GENERATION_STATUS_RUNNING


def _running_finish(
    entry: QueueEntry | None, now: datetime, average: float
) -> datetime:
    if entry is None:
        return now
    elapsed = _elapsed_minutes(entry.started_at, now)
    remaining = max(average - elapsed, 0.0)
    return now + timedelta(minutes=remaining)


def _elapsed_minutes(started_at: datetime | None, now: datetime) -> float:
    if started_at is None:
        return 0.0
    seconds = (_aware(now) - _aware(started_at)).total_seconds()
    return max(seconds, 0.0) / _SECONDS_PER_MINUTE


def _entry_start(entry: QueueEntry, available: datetime) -> datetime:
    if entry.status != GENERATION_STATUS_RETRY_WAIT or entry.next_attempt_at is None:
        return available
    return max(available, _aware(entry.next_attempt_at))


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _short(title: str) -> str:
    if len(title) <= LIST_TITLE_MAX_CHARS:
        return title
    return title[: LIST_TITLE_MAX_CHARS - 1] + ELLIPSIS


__all__ = [
    "QueueControl",
    "QueueEntry",
    "QueuePlacement",
    "QueuePosition",
    "QueueSnapshot",
    "average_drive_minutes",
    "joined_titles",
    "local_time",
    "position_of",
    "position_text",
    "queue_placements",
]
