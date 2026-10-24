"""The web's queue monitor: read the numbers every minute, alert once per episode."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import structlog

from rag_backend.modules.generation_queue.constants import (
    LOG_PERIODIC_FAILED,
    LOG_QUEUE_ALERT,
    MONITOR_INTERVAL_SECONDS,
)
from rag_backend.modules.generation_queue.domain.health import (
    QueueAlertPolicy,
    QueueMetrics,
)
from rag_backend.modules.generation_queue.domain.ports import Clock

logger = structlog.get_logger()

MetricsReader = Callable[[], Awaitable[QueueMetrics]]
AlertSender = Callable[[str], None]


@dataclass(frozen=True, kw_only=True)
class MonitorDependencies:
    """What the monitor reads and where it alerts."""

    read: MetricsReader
    alert: AlertSender
    clock: Clock


async def monitor_once(deps: MonitorDependencies, policy: QueueAlertPolicy) -> int:
    """One reading; returns how many alerts it sent."""
    texts = policy.evaluate(await deps.read(), deps.clock.now())
    for message in texts:
        logger.warning(LOG_QUEUE_ALERT, message=message)
        deps.alert(message)
    return len(texts)


async def run_monitor(deps: MonitorDependencies, stop: asyncio.Event) -> None:
    """Read and alert every minute until ``stop`` is set."""
    policy = QueueAlertPolicy()
    while not stop.is_set():
        try:
            await monitor_once(deps, policy)
        except Exception:
            logger.exception(LOG_PERIODIC_FAILED, step="queue_monitor", exc_info=True)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=MONITOR_INTERVAL_SECONDS)


__all__ = ["MonitorDependencies", "monitor_once", "run_monitor"]
