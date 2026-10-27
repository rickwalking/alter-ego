"""Safe generation-log API contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from rag_backend.modules.generation_queue.events_public import (
    EventDetail,
    GenerationLogPage,
)


class GenerationLogPageQuery(BaseModel):
    """A bounded event page and its optional keyset cursor."""

    limit: int = Field(default=50, ge=1, le=200)
    before: UUID | None = None


class GenerationEventResponse(BaseModel):
    """One content-free generation event."""

    id: UUID
    generation_run_id: UUID
    event_type: str
    phase: str | None
    outcome: str
    occurred_at: datetime
    duration_ms: int | None
    attempt: int | None
    error_code: str | None
    message_code: str | None
    details: dict[str, EventDetail]
    langfuse_trace_id: str | None
    langfuse_trace_url: str | None


class GenerationRunResponse(BaseModel):
    """The current safe queue fields of one referenced run."""

    id: UUID
    kind: str
    status: str
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    attempts: int
    error_code: str | None


class CarouselGenerationLogResponse(BaseModel):
    """One event page and the runs needed to group it."""

    project_id: UUID
    events: list[GenerationEventResponse]
    runs: list[GenerationRunResponse]
    next_cursor: UUID | None


def generation_log_response(
    project_id: UUID, page: GenerationLogPage
) -> CarouselGenerationLogResponse:
    """Map domain values without exposing payloads or raw errors."""
    return CarouselGenerationLogResponse(
        project_id=project_id,
        events=[
            GenerationEventResponse.model_validate(event, from_attributes=True)
            for event in page.events
        ],
        runs=[
            GenerationRunResponse(
                id=run.id,
                kind=run.kind.value,
                status=run.status,
                queued_at=run.queued_at,
                started_at=run.started_at,
                finished_at=run.finished_at,
                duration_ms=_run_duration(run.started_at, run.finished_at),
                attempts=run.attempts,
                error_code=run.error_code,
            )
            for run in page.runs
        ],
        next_cursor=page.next_cursor,
    )


def _run_duration(started: datetime | None, finished: datetime | None) -> int | None:
    if started is None or finished is None:
        return None
    return max(0, round((finished - started).total_seconds() * 1000))


__all__ = [
    "CarouselGenerationLogResponse",
    "GenerationLogPageQuery",
    "generation_log_response",
]
