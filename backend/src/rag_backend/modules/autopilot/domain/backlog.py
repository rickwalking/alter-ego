"""Themes that did not fit the daily cap wait for the next morning (Pedro).

A backlog theme is a stored topic candidate in a waiting status. The next scout
batch gives the day's free slots to the backlog first, oldest first; a theme stored
today waits until tomorrow. At most ``BACKLOG_MAX`` themes wait; a theme older than
``BACKLOG_EXPIRY_DAYS`` expires. Radar IA (news) topics never wait: they go stale and
are capped per week. "Gerar agora" queues one theme at once, outside the daily cap.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.queue_constants import (
    BACKLOG_EXPIRY_DAYS,
    BACKLOG_MAX,
    BACKLOG_WAITING,
)


@dataclass(frozen=True, kw_only=True)
class BacklogTheme:
    """One waiting theme."""

    candidate_id: UUID
    title: str
    created_at: datetime


@dataclass(frozen=True, kw_only=True)
class BacklogWindow:
    """Themes stored before ``before`` and not before ``since``."""

    since: datetime
    before: datetime


@dataclass(frozen=True, kw_only=True)
class BacklogChange:
    """Move the listed candidates still in one of ``expected`` to ``status``."""

    candidate_ids: tuple[UUID, ...]
    status: str
    expected: tuple[str, ...] = BACKLOG_WAITING


@dataclass(frozen=True, kw_only=True)
class GenerateNowCommand:
    """Queue one waiting theme now as run ``run_id``."""

    candidate_id: UUID
    run_id: UUID
    created_at: datetime


class BacklogStore(Protocol):
    """Backlog reads and writes; the caller commits."""

    async def waiting(self, window: BacklogWindow) -> list[BacklogTheme]:
        """Waiting themes in the window, oldest first."""
        ...

    async def change(self, change: BacklogChange) -> tuple[UUID, ...]:
        """Compare-and-set the status; the ids that actually moved."""
        ...

    async def unannounced(self) -> list[BacklogTheme]:
        """Themes that joined the backlog and were not announced yet, oldest first."""
        ...

    async def generate_now(self, command: GenerateNowCommand) -> BacklogTheme | None:
        """Take a waiting theme out of the backlog and queue its run, once."""
        ...


class NoBacklog:
    """A ``BacklogStore`` with nothing in it (tests and partial wiring)."""

    @staticmethod
    async def waiting(window: BacklogWindow) -> list[BacklogTheme]:
        """Nothing waits."""
        del window
        return []

    @staticmethod
    async def change(change: BacklogChange) -> tuple[UUID, ...]:
        """Nothing moves."""
        del change
        return ()

    @staticmethod
    async def unannounced() -> list[BacklogTheme]:
        """Nothing to announce."""
        return []

    @staticmethod
    async def generate_now(command: GenerateNowCommand) -> BacklogTheme | None:
        """Nothing to queue."""
        del command
        return None


def expiry_cutoff(now: datetime) -> datetime:
    """Themes stored before this moment have waited too long."""
    return now - timedelta(days=BACKLOG_EXPIRY_DAYS)


def promotable(waiting: Sequence[BacklogTheme], room: int) -> tuple[UUID, ...]:
    """The oldest waiting themes that fit the day's free slots."""
    if room <= 0:
        return ()
    return tuple(theme.candidate_id for theme in waiting[:room])


def backlog_room(waiting_count: int, promoted: int) -> int:
    """How many new themes may still join the backlog."""
    return max(BACKLOG_MAX - (waiting_count - promoted), 0)


__all__ = [
    "BacklogChange",
    "BacklogStore",
    "BacklogTheme",
    "BacklogWindow",
    "GenerateNowCommand",
    "NoBacklog",
    "backlog_room",
    "expiry_cutoff",
    "promotable",
]
