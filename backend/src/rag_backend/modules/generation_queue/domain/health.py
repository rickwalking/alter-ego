"""Queue health: the numbers ``/health/ready`` reports and when to alert Pedro.

The alerts fire once per episode: the worker missing for 10 min, or the oldest
queued run waiting more than 6 h. An episode ends when the
condition clears, so the next one alerts again.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rag_backend.modules.generation_queue.constants import (
    ALERT_QUEUE_STALLED,
    ALERT_WORKER_MISSING,
    OLDEST_QUEUED_ALERT_SECONDS,
    WORKER_MISSING_ALERT_SECONDS,
)

_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR = 3600


@dataclass(frozen=True, kw_only=True)
class QueueMetrics:
    """One reading of the queue."""

    queued: int
    running: int
    retry_wait: int
    dead_letters: int
    oldest_queued_seconds: int
    running_seconds: int
    worker_connected: bool

    def as_check(self) -> dict[str, str | int]:
        """The ``/health/ready`` entry (numbers only, no ids)."""
        return {
            "status": "ok" if self.worker_connected else "worker_down",
            "queued": self.queued,
            "running": self.running,
            "retry_wait": self.retry_wait,
            "dead_letters": self.dead_letters,
            "oldest_queued_seconds": self.oldest_queued_seconds,
            "running_seconds": self.running_seconds,
        }


@dataclass
class QueueAlertPolicy:
    """Remembers the open episodes between readings."""

    worker_missing_since: datetime | None = None
    worker_alerted: bool = False
    stall_alerted: bool = False

    def evaluate(self, metrics: QueueMetrics, now: datetime) -> list[str]:
        """The alert texts this reading should send (usually none)."""
        return [*self._worker(metrics, now), *self._stall(metrics)]

    def _worker(self, metrics: QueueMetrics, now: datetime) -> list[str]:
        if metrics.worker_connected:
            self.worker_missing_since = None
            self.worker_alerted = False
            return []
        if self.worker_missing_since is None:
            self.worker_missing_since = now
        missing = (now - self.worker_missing_since).total_seconds()
        if self.worker_alerted or missing < WORKER_MISSING_ALERT_SECONDS:
            return []
        self.worker_alerted = True
        minutes = int(missing // _SECONDS_PER_MINUTE)
        return [ALERT_WORKER_MISSING.format(minutes=minutes)]

    def _stall(self, metrics: QueueMetrics) -> list[str]:
        if metrics.oldest_queued_seconds <= OLDEST_QUEUED_ALERT_SECONDS:
            self.stall_alerted = False
            return []
        if self.stall_alerted:
            return []
        self.stall_alerted = True
        hours = metrics.oldest_queued_seconds // _SECONDS_PER_HOUR
        return [ALERT_QUEUE_STALLED.format(hours=hours, queued=metrics.queued)]


__all__ = ["QueueAlertPolicy", "QueueMetrics"]
