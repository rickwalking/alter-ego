"""Tracked in-process scheduling of cover generation runs.

The 202 route records the pending generation and hands the run here:
``asyncio.create_task`` plus a module-level set, the same mechanism as the
blog generation runner. A restart kills the task; the row is then failed as
interrupted the next time the carousel's generations are read.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import structlog

from rag_backend.domain.constants.cover_generation import (
    LOG_COVER_GENERATION_CRASHED,
    TASK_NAME_PREFIX,
)

logger = structlog.get_logger(__name__)

_background_tasks: set[asyncio.Task[None]] = set()


async def _guarded(run: Callable[[], Awaitable[object]], generation_id: str) -> None:
    try:
        await run()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(LOG_COVER_GENERATION_CRASHED, generation_id=generation_id)


def schedule_cover_generation(
    run: Callable[[], Awaitable[object]], generation_id: str
) -> asyncio.Task[None]:
    """Fire-and-forget ``run``, tracked so it is not garbage-collected."""
    task = asyncio.create_task(
        _guarded(run, generation_id), name=f"{TASK_NAME_PREFIX}{generation_id}"
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


def running_cover_generation_tasks() -> frozenset[asyncio.Task[None]]:
    """The in-flight runs of this process (read-only view)."""
    return frozenset(_background_tasks)


__all__ = ["running_cover_generation_tasks", "schedule_cover_generation"]
