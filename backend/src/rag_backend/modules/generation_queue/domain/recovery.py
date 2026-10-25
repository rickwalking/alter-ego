"""The daily recovery scan's ports and report (04:00 São Paulo time, once a day).

The scan retries once the autopilot runs the queue parked for a transient-class
reason in the last 7 days, resumes autopilot runs escalated as stale in the last
72 hours, lists the dashboard projects left in progress with nothing queued (they
stay parked: Pedro resumes them from the editor), purges old succeeded runs and
PgQueuer log rows, and sends Pedro one summary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class ParkedDrive:
    """A dead-lettered autopilot drive the scan may retry once."""

    generation_run_id: UUID
    autopilot_run_id: str


@dataclass(frozen=True, kw_only=True)
class ScanReport:
    """What one scan did; ``interactive`` holds the parked dashboard projects."""

    recovered: int = 0
    still_dead: int = 0
    queued: int = 0
    purged_runs: int = 0
    purged_logs: int = 0
    interactive: tuple[str, ...] = field(default_factory=tuple)


class RecoveryStore(Protocol):
    """The queue's own reads and writes for the scan; each call commits."""

    async def recoverable(self, since: datetime) -> list[ParkedDrive]:
        """Untried autopilot dead letters since ``since`` (transient-class codes)."""
        ...

    async def mark_attempted(self, generation_run_id: UUID) -> bool:
        """Mark the dead letter tried once (compare-and-set); False when already."""
        ...

    async def dead_letters(self, since: datetime) -> int:
        """How many generation runs were dead-lettered since ``since``."""
        ...

    async def active(self) -> int:
        """How many generation runs are queued, running or waiting for a retry."""
        ...

    async def interactive_orphans(self) -> list[str]:
        """Titles of dashboard projects in progress with nothing queued."""
        ...

    async def purge(self, before: datetime) -> tuple[int, int]:
        """Delete succeeded runs and PgQueuer log rows older than ``before``."""
        ...


class ParkedAutopilot(Protocol):
    """The autopilot side of the scan (the queue bridge)."""

    async def revive_dead_letter(self, run_id: str) -> bool:
        """Retry a run the queue parked; False when it is no longer parked."""
        ...

    async def revive_stale(self, since: datetime) -> int:
        """Resume runs escalated as stale since ``since``; how many moved."""
        ...


__all__ = ["ParkedAutopilot", "ParkedDrive", "RecoveryStore", "ScanReport"]
