"""Ports for Grok Bot scout intake.

The domain names the writes. Infrastructure implements them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from rag_backend.modules.autopilot.domain.notify import StatusNotice, StatusSendResult
from rag_backend.modules.autopilot.domain.x_observation import AcceptedObservation


@dataclass(frozen=True, kw_only=True)
class SaveXSignals:
    """Accepted observations to upsert, stamped with one clock reading."""

    rows: tuple[AcceptedObservation, ...]
    stored_at: datetime


class XSignalStore(Protocol):
    """Persists browser signals and refreshes their allowlist rows."""

    async def save(self, command: SaveXSignals) -> None:
        """Upsert the rows and remember their URLs for topic intake."""
        ...

    async def commit(self) -> None:
        """Commit the current unit of work."""
        ...


class StatusSender(Protocol):
    """Sends one owner status message. AE-0355's notifier implements this."""

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        """Deliver ``notice`` and return the message id."""
        ...


@dataclass(frozen=True, kw_only=True)
class ScoutFailureEntry:
    """One delivered scout failure, kept for the daily cap and dedupe."""

    reason: str
    sent_at: datetime


class ScoutFailureLog(Protocol):
    """Remembers delivered scout failures. The caller commits."""

    async def lock(self) -> None:
        """Hold the cap lock until the next commit (QA r2 R7)."""
        ...

    async def reasons_since(self, since: datetime) -> tuple[str, ...]:
        """Reasons delivered at or after ``since``, oldest first."""
        ...

    async def record(self, entry: ScoutFailureEntry) -> None:
        """Stage one delivered failure."""
        ...

    async def commit(self) -> None:
        """Commit the current unit of work."""
        ...
