"""Durable maintenance commands, dedupe identities and enqueue results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from rag_backend.modules.generation_queue.constants import (
    MAINTENANCE_DISPATCH_PREFIX,
    MAINTENANCE_FULL,
)


@dataclass(frozen=True)
class MaintenanceCommand:
    """A full pass, or dispatch for exactly one generation run."""

    run_id: UUID | None = None

    @property
    def dedupe_key(self) -> str:
        """The complete active-job dedupe identity."""
        if self.run_id is None:
            return MAINTENANCE_FULL
        return f"{MAINTENANCE_DISPATCH_PREFIX}{self.run_id}"

    @property
    def payload(self) -> bytes:
        """The self-contained worker payload."""
        return self.dedupe_key.encode()


@dataclass(frozen=True)
class MaintenanceEnqueue:
    """Whether a job was inserted or an active dedupe match was returned."""

    job_id: int | None
    inserted: bool


class MaintenanceOutcome(StrEnum):
    """The observable result of one control job."""

    DISPATCHED = "dispatched"
    COMPLETED = "completed"
    BUSY = "busy"
    IGNORED = "ignored"


class FullMaintenanceControl(Protocol):
    """The shared manual and cron full-pass enqueue port."""

    async def request_full(self) -> MaintenanceEnqueue:
        """Insert or find the active full control job."""
        ...


def parse_maintenance(payload: bytes | None) -> MaintenanceCommand | None:
    """Parse only a complete full or dispatch payload; ignore foreign jobs."""
    if not payload:
        return None
    try:
        text = payload.decode()
        if text == MAINTENANCE_FULL:
            return MaintenanceCommand()
        if not text.startswith(MAINTENANCE_DISPATCH_PREFIX):
            return None
        run_id = UUID(text.removeprefix(MAINTENANCE_DISPATCH_PREFIX))
    except (UnicodeDecodeError, ValueError):
        return None
    return MaintenanceCommand(run_id=run_id)


__all__ = [
    "FullMaintenanceControl",
    "MaintenanceCommand",
    "MaintenanceEnqueue",
    "MaintenanceOutcome",
    "parse_maintenance",
]
