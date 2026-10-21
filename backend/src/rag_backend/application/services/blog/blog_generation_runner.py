"""Tracked in-process scheduling of blog generation runs (AE-0425, ADR-0025).

The 202 routes persist the draft and hand the run to :func:`schedule_blog_generation`:
``asyncio.create_task`` + the module-level ``_background_tasks`` set + a task
name, the same mechanism as
``editorial_workflow_resume_runner.schedule_background_resume``. No FastAPI
``BackgroundTasks``, Celery or ARQ. A restart kills the task; the row is then
recovered by the worker-tick reaper (``BlogGenerationReaper``), and
:func:`cancel_blog_generation_tasks` cancels in-flight runs on shutdown (each
marks its row recoverable-failed before it stops).
"""

from __future__ import annotations

import asyncio
from typing import Protocol

import structlog

from rag_backend.application.services.blog.blog_generation_service import (
    GenerationJob,
)
from rag_backend.domain.constants.blog_generation import (
    LOG_GENERATION_FAILED,
    TASK_NAME_PREFIX,
)
from rag_backend.domain.models.blog_generation import GenerationOutcome
from rag_backend.infrastructure.langfuse_client import flush_langfuse

logger = structlog.get_logger(__name__)

_background_tasks: set[asyncio.Task[None]] = set()


class GenerationRunner(Protocol):
    """What the runner schedules (``BlogGenerationService`` satisfies it)."""

    async def run(self, job: GenerationJob) -> GenerationOutcome | None:
        """Run one job to its recorded outcome."""
        ...


async def _run(service: GenerationRunner, job: GenerationJob) -> None:
    try:
        await service.run(job)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(LOG_GENERATION_FAILED, post_id=job.lease.post_id)
    finally:
        flush_langfuse()


def schedule_blog_generation(
    service: GenerationRunner, job: GenerationJob
) -> asyncio.Task[None]:
    """Fire-and-forget the run, tracked so shutdown can cancel it."""
    task = asyncio.create_task(
        _run(service, job), name=f"{TASK_NAME_PREFIX}{job.lease.post_id}"
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


def running_blog_generation_tasks() -> frozenset[asyncio.Task[None]]:
    """The in-flight runs of this process (read-only view)."""
    return frozenset(_background_tasks)


async def cancel_blog_generation_tasks() -> int:
    """Cancel every in-flight run and wait for it to record its failure."""
    tasks = [task for task in _background_tasks if not task.done()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    return len(tasks)


__all__ = [
    "GenerationRunner",
    "cancel_blog_generation_tasks",
    "running_blog_generation_tasks",
    "schedule_blog_generation",
]
