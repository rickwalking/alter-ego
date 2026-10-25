"""Where a run sits in the generation queue and when it should start. Pure.

The worker drives one carousel at a time in strict FIFO order (Pedro): first the
active generation runs by creation, then the autopilot runs the dispatcher has not
picked up yet, by their own creation (the order it stages them). The start estimate
is ``now`` plus one average recent drive per run ahead.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from rag_backend.modules.autopilot.queue_constants import (
    DEFAULT_DRIVE_MINUTES,
    ELLIPSIS,
    ETA_FORMAT,
    LIST_SEPARATOR,
    LIST_TITLE_MAX_CHARS,
    QUEUE_TIMEZONE,
    TEXT_QUEUE_POSITION,
)


@dataclass(frozen=True, kw_only=True)
class QueueSnapshot:
    """The queue order and recent drive times.

    ``ahead`` holds the autopilot run ids (or None for dashboard work) of the
    active generation runs, oldest first; ``waiting`` the driven autopilot runs
    without an active generation run, oldest first.
    """

    ahead: tuple[str | None, ...]
    waiting: tuple[str, ...]
    drive_minutes: tuple[float, ...] = ()


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


def average_drive_minutes(drives: Sequence[float]) -> float:
    """The mean of the recent drives, or the default without history."""
    if not drives:
        return float(DEFAULT_DRIVE_MINUTES)
    return sum(drives) / len(drives)


def position_of(
    snapshot: QueueSnapshot, run_id: UUID, now: datetime
) -> QueuePosition | None:
    """The run's position and estimated start; None when it is not queued."""
    order = (*snapshot.ahead, *snapshot.waiting)
    key = str(run_id)
    if key not in order:
        return None
    position = order.index(key) + 1
    minutes = average_drive_minutes(snapshot.drive_minutes) * (position - 1)
    return QueuePosition(
        position=position, total=len(order), eta=now + timedelta(minutes=minutes)
    )


def position_text(position: QueuePosition) -> str:
    """``Na fila: posição N de M — início estimado HH:MM`` (São Paulo time)."""
    return TEXT_QUEUE_POSITION.format(
        position=position.position, total=position.total, eta=local_time(position.eta)
    )


def joined_titles(titles: Iterable[str]) -> str:
    """Titles joined for one message, each cut to ``LIST_TITLE_MAX_CHARS``."""
    return LIST_SEPARATOR.join(_short(title) for title in titles)


def _short(title: str) -> str:
    if len(title) <= LIST_TITLE_MAX_CHARS:
        return title
    return title[: LIST_TITLE_MAX_CHARS - 1] + ELLIPSIS


def local_time(moment: datetime) -> str:
    """``HH:MM`` in São Paulo time."""
    return moment.astimezone(ZoneInfo(QUEUE_TIMEZONE)).strftime(ETA_FORMAT)


__all__ = [
    "QueueControl",
    "QueuePosition",
    "QueueSnapshot",
    "average_drive_minutes",
    "joined_titles",
    "local_time",
    "position_of",
    "position_text",
]
