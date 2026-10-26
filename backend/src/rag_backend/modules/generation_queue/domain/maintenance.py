"""Durable maintenance commands, dedupe identities and enqueue results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from rag_backend.modules.generation_queue.constants import (
    MAINTENANCE_DISPATCH_PREFIX,
    MAINTENANCE_FULL,
    MAINTENANCE_PROMOTE,
    MAINTENANCE_SCAN,
)


class MaintenanceMode(StrEnum):
    """The independent scheduled and manual maintenance passes."""

    PROMOTE = MAINTENANCE_PROMOTE
    SCAN = MAINTENANCE_SCAN
    FULL = MAINTENANCE_FULL


@dataclass(frozen=True)
class MaintenanceCommand:
    """A mode-specific pass, or dispatch for exactly one generation run."""

    run_id: UUID | None = None
    mode: MaintenanceMode = MaintenanceMode.FULL

    @property
    def dedupe_key(self) -> str:
        """The complete active-job dedupe identity."""
        if self.run_id is None:
            return self.mode.value
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
    SUBSUMED = "subsumed"
    IGNORED = "ignored"


class MaintenanceControl(Protocol):
    """The mode-specific durable maintenance enqueue port."""

    async def request(self, mode: MaintenanceMode) -> MaintenanceEnqueue:
        """Insert or find the active control job for one mode."""
        ...


class FullMaintenanceControl(Protocol):
    """The manual full-pass enqueue port."""

    async def request_full(self) -> MaintenanceEnqueue:
        """Insert or find the active full control job."""
        ...


def parse_maintenance(payload: bytes | None) -> MaintenanceCommand | None:
    """Parse only a complete maintenance or dispatch payload."""
    if not payload:
        return None
    try:
        text = payload.decode()
        if text.startswith(MAINTENANCE_DISPATCH_PREFIX):
            run_id = UUID(text.removeprefix(MAINTENANCE_DISPATCH_PREFIX))
            return MaintenanceCommand(run_id=run_id)
        return MaintenanceCommand(mode=MaintenanceMode(text))
    except (UnicodeDecodeError, ValueError):
        return None


__all__ = [
    "FullMaintenanceControl",
    "MaintenanceCommand",
    "MaintenanceControl",
    "MaintenanceEnqueue",
    "MaintenanceMode",
    "MaintenanceOutcome",
    "parse_maintenance",
]
