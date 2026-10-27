"""Run-scoped, best-effort generation-event recording."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass

import structlog

from rag_backend.modules.generation_queue.domain.failure_metadata import (
    safe_failure_metadata,
)
from rag_backend.modules.generation_queue.domain.generation_events import (
    EVENT_WRITE_TIMEOUT_SECONDS,
    GenerationEventInput,
    GenerationEventRecorder,
    GenerationEventRun,
    sanitize_event,
)
from rag_backend.modules.generation_queue.domain.models import GenerationRun

LOG_EVENT_STORE_FAILED = "generation_event_store_failed"


@dataclass
class GenerationEventScope:
    """One job's identity and destination, never an event buffer."""

    run: GenerationEventRun
    recorder: GenerationEventRecorder
    project_id: str | None = None

    def __post_init__(self) -> None:
        if self.project_id is None:
            self.project_id = self.run.carousel_project_id


class _NoEventRecorder:
    @staticmethod
    async def record(run: GenerationEventRun, event: GenerationEventInput) -> bool:
        del run, event
        return False


class _NoRunCompletion:
    @staticmethod
    async def completed(project_id: str, *, succeeded: bool = True) -> None:
        del project_id, succeeded


NO_EVENT_RECORDER = _NoEventRecorder()
NO_RUN_COMPLETION = _NoRunCompletion()
_SCOPE: ContextVar[GenerationEventScope | None] = ContextVar(
    "carousel_generation_event_scope", default=None
)
logger = structlog.get_logger()


@asynccontextmanager
async def generation_event_scope(
    run: GenerationEventRun, recorder: GenerationEventRecorder
) -> AsyncIterator[None]:
    """Bind one generation run for the current task and its children."""
    token = _SCOPE.set(GenerationEventScope(run=run, recorder=recorder))
    try:
        yield
    finally:
        _SCOPE.reset(token)


def generation_event_run(run: GenerationRun) -> GenerationEventRun:
    """Convert the queue's run into its safe event identity."""
    return GenerationEventRun(
        id=run.id,
        kind=run.kind,
        carousel_project_id=run.carousel_project_id,
        autopilot_run_id=run.autopilot_run_id,
    )


def set_generation_event_project(project_id: str) -> None:
    """Associate later events once autopilot has assigned its carousel."""
    scope = _SCOPE.get()
    if scope is not None and scope.project_id is None:
        scope.project_id = project_id


def current_generation_event_project() -> str | None:
    """The project resolved for the active event scope, if assigned."""
    scope = _SCOPE.get()
    return scope.project_id if scope is not None else None


async def record_generation_event(event: GenerationEventInput) -> bool:
    """Write one bounded event without affecting the generation outcome."""
    scope = _SCOPE.get()
    if scope is None or scope.project_id is None:
        return False
    run = GenerationEventRun(
        id=scope.run.id,
        kind=scope.run.kind,
        carousel_project_id=scope.project_id,
        autopilot_run_id=scope.run.autopilot_run_id,
    )
    try:
        async with asyncio.timeout(EVENT_WRITE_TIMEOUT_SECONDS):
            safe = sanitize_event(event)
            return await scope.recorder.record(run, safe)
    except Exception as exc:
        logger.warning(
            LOG_EVENT_STORE_FAILED,
            event_type=event.event_type,
            **safe_failure_metadata(exc),
        )
        return False


__all__ = [
    "NO_EVENT_RECORDER",
    "NO_RUN_COMPLETION",
    "GenerationEventScope",
    "current_generation_event_project",
    "generation_event_run",
    "generation_event_scope",
    "record_generation_event",
    "set_generation_event_project",
]
