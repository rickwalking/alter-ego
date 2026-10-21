"""Interval heartbeat task for a run-owned workflow resume.

The run wrapper starts the loop when it owns a run fence and stops it on every
exit path. Stopping waits for the task to finish: a loop caught inside a
heartbeat write must not outlive the run that owns it.
"""

from __future__ import annotations

import asyncio

from rag_backend.domain.constants.carousel_run import (
    DEFAULT_RUN_HEARTBEAT_INTERVAL_SECONDS,
)
from rag_backend.domain.models.carousel_run import CarouselRunContext
from rag_backend.modules.editorial.public import write_run_heartbeat_with_retry


async def run_heartbeat_loop(ctx: CarouselRunContext) -> None:
    """Heartbeat run_heartbeat_at until cancelled or the fence is lost.

    The interval is the domain default (60s); the write itself retries on
    transient failure and is self-fencing (epoch pinned in its WHERE clause).
    """
    while True:
        await asyncio.sleep(DEFAULT_RUN_HEARTBEAT_INTERVAL_SECONDS)
        if not await write_run_heartbeat_with_retry(ctx.project_id, ctx.epoch):
            return


def start_heartbeat(fence: CarouselRunContext | None) -> asyncio.Task[None] | None:
    """Start the interval heartbeat for an owned run; None without a fence."""
    if fence is None:
        return None
    return asyncio.create_task(run_heartbeat_loop(fence))


async def stop_heartbeat(heartbeat: asyncio.Task[None] | None) -> None:
    """Cancel the heartbeat loop and wait until it has really finished.

    ``cancel()`` alone only requests the stop. A loop caught inside a
    write outlived the run, wrote after the run's connections were gone, and
    hung event-loop shutdown waiting on that write (CI "Test & Coverage" ran
    ~3h). ``asyncio.wait`` never raises the heartbeat's own CancelledError,
    while a cancel of the calling run still propagates.
    """
    if heartbeat is None:
        return
    heartbeat.cancel()
    await asyncio.wait((heartbeat,))


__all__ = ["run_heartbeat_loop", "start_heartbeat", "stop_heartbeat"]
