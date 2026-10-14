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
