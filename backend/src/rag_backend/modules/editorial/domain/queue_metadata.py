"""Project metadata exposed to queue readers outside editorial."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class ProjectQueueMetadata:
    """Current phase, lock version and actual run heartbeat of one project."""

    current_phase: str
    lock_version: int
    heartbeat_at: datetime | None


__all__ = ["ProjectQueueMetadata"]
