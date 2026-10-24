"""The worker's loops: the dispatcher every 10 s, the heavy periodic steps every tick.

The heavy steps moved here from the web loop: the
stale-run reaper first, then the drift reconciler (it stamps the row's current
epoch, so it must follow the reaper), the republish sweeper (it renders PDFs) and
the autopilot sweep (expiries, escalation wake). Each step commits on its own, so
one failure never rolls back the others. The dispatcher pass also touches the
liveness file the container healthcheck reads.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.domain.protocols.carousel_run import (
    CarouselDriftReconciler,
    CarouselRepublishSweeper,
    CarouselStaleRunReaper,
)
from rag_backend.modules.autopilot.queue_bridge import AutopilotQueueBridge
from rag_backend.modules.generation_queue.application.dispatcher import Dispatcher
from rag_backend.modules.generation_queue.constants import (
    DISPATCH_INTERVAL_SECONDS,
    LOG_DISPATCH_FAILED,
    LOG_PERIODIC_FAILED,
)

logger = structlog.get_logger()

DbStep = Callable[[AsyncSession], Awaitable[int]]
StopSignal = Callable[[], asyncio.Event]


@dataclass(frozen=True, kw_only=True)
class PeriodicSteps:
    """The heavy steps the worker owns."""

    sessions: async_sessionmaker[AsyncSession]
    reaper: CarouselStaleRunReaper
    drift: CarouselDriftReconciler | None
    republish: CarouselRepublishSweeper
    bridge: AutopilotQueueBridge


async def _sleep_or_stop(stop: StopSignal, seconds: float) -> None:
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(stop().wait(), timeout=seconds)


async def _db_step(steps: PeriodicSteps, name: str, step: DbStep) -> None:
    try:
        async with steps.sessions() as session:
            await step(session)
            await session.commit()
    except Exception:
        logger.exception(LOG_PERIODIC_FAILED, step=name, exc_info=True)


async def run_periodic_once(steps: PeriodicSteps) -> None:
    """Reaper, drift reconciler, republish sweeper, autopilot sweep, in order."""
    await _db_step(steps, "reaper", steps.reaper.tick)
    if steps.drift is not None:
        await _db_step(steps, "drift", steps.drift.reconcile)
    await _db_step(steps, "republish", steps.republish.sweep)
    try:
        await steps.bridge.sweep()
    except Exception:
        logger.exception(LOG_PERIODIC_FAILED, step="autopilot_sweep", exc_info=True)


async def run_periodic(steps: PeriodicSteps, stop: StopSignal, interval: float) -> None:
    """Run the heavy steps every ``interval`` seconds until ``stop`` is set."""
    while not stop().is_set():
        await run_periodic_once(steps)
        await _sleep_or_stop(stop, interval)


async def run_dispatcher(
    dispatcher: Dispatcher, stop: StopSignal, alive_file: str
) -> None:
    """A dispatcher pass every 10 s until ``stop``; each marks the worker alive."""
    while not stop().is_set():
        try:
            await dispatcher.run_once()
            Path(alive_file).touch()
        except Exception:
            logger.exception(LOG_DISPATCH_FAILED, exc_info=True)
        await _sleep_or_stop(stop, DISPATCH_INTERVAL_SECONDS)


__all__ = [
    "PeriodicSteps",
    "StopSignal",
    "run_dispatcher",
    "run_periodic",
    "run_periodic_once",
]
