"""SQL persistence and bounded keyset reads for generation events."""

from __future__ import annotations

from sqlalchemy import (
    ColumnElement,
    Select,
    Uuid,
    and_,
    cast,
    exists,
    literal,
    or_,
    select,
    tuple_,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.generation_queue.domain.generation_events import (
    GenerationEvent,
    GenerationEventInput,
    GenerationEventRun,
    GenerationLogPage,
    GenerationLogQuery,
    GenerationRunSummary,
    InvalidGenerationEventCursorError,
    sanitize_event,
    sanitize_event_details,
)
from rag_backend.modules.generation_queue.domain.models import GenerationKind
from rag_backend.modules.generation_queue.infrastructure.models import (
    CarouselGenerationEventModel,
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.repository import (
    _autopilot_uuid,
)


class SqlGenerationEventRecorder:
    """Insert one sanitized event in its own short transaction."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def record(
        self, run: GenerationEventRun, event: GenerationEventInput
    ) -> bool:
        """Insert immediately without retaining event state."""
        if run.carousel_project_id is None:
            return False
        safe = sanitize_event(event)
        async with self._sessions() as session:
            run_row = await session.get(GenerationRunModel, run.id)
            if not await _compatible_run(session, run_row, run):
                return False
            session.add(
                CarouselGenerationEventModel(
                    id=safe.id,
                    generation_run_id=run.id,
                    carousel_project_id=run.carousel_project_id,
                    kind=run.kind.value,
                    event_type=safe.event_type,
                    phase=safe.phase,
                    outcome=safe.outcome,
                    occurred_at=safe.occurred_at,
                    duration_ms=safe.duration_ms,
                    attempt=safe.attempt,
                    error_code=safe.error_code,
                    message_code=safe.message_code,
                    details=safe.details,
                    langfuse_trace_id=safe.langfuse_trace_id,
                    langfuse_trace_url=safe.langfuse_trace_url,
                )
            )
            await session.commit()
        return True


async def _compatible_run(
    session: AsyncSession, row: GenerationRunModel | None, run: GenerationEventRun
) -> bool:
    if row is None or row.kind != run.kind.value:
        return False
    if row.carousel_project_id is not None:
        return row.carousel_project_id == run.carousel_project_id
    if run.kind is not GenerationKind.AUTOPILOT_DRIVE or run.autopilot_run_id is None:
        return False
    parent_id = _autopilot_uuid(run.autopilot_run_id)
    if parent_id is None:
        return False
    parent = await session.get(AutopilotRunModel, parent_id)
    return parent is not None and parent.carousel_project_id == run.carousel_project_id


async def read_generation_log(
    session: AsyncSession, query: GenerationLogQuery
) -> GenerationLogPage:
    """Read one stable page and only its referenced run summaries."""
    rows = await _event_rows(session, query)
    visible = rows[: query.limit]
    events = tuple(_event_from_row(row) for row in visible)
    runs = await _run_summaries(session, events, query.project_id)
    next_cursor = visible[-1].id if len(rows) > query.limit and visible else None
    return GenerationLogPage(events=events, runs=runs, next_cursor=next_cursor)


async def _event_rows(
    session: AsyncSession, query: GenerationLogQuery
) -> list[CarouselGenerationEventModel]:
    statement: Select[tuple[CarouselGenerationEventModel]] = (
        select(CarouselGenerationEventModel)
        .join(
            GenerationRunModel,
            CarouselGenerationEventModel.generation_run_id == GenerationRunModel.id,
        )
        .where(
            CarouselGenerationEventModel.carousel_project_id == query.project_id,
            _project_condition(query.project_id),
        )
    )
    if query.before is not None:
        anchor = await _cursor_row(session, query)
        statement = statement.where(
            tuple_(
                CarouselGenerationEventModel.occurred_at,
                CarouselGenerationEventModel.id,
            )
            < tuple_(literal(anchor.occurred_at), literal(anchor.id))
        )
    result = await session.scalars(
        statement.order_by(
            CarouselGenerationEventModel.occurred_at.desc(),
            CarouselGenerationEventModel.id.desc(),
        ).limit(query.limit + 1)
    )
    return list(result.all())


async def _cursor_row(
    session: AsyncSession, query: GenerationLogQuery
) -> CarouselGenerationEventModel:
    anchor = await session.scalar(
        select(CarouselGenerationEventModel)
        .join(
            GenerationRunModel,
            CarouselGenerationEventModel.generation_run_id == GenerationRunModel.id,
        )
        .where(
            CarouselGenerationEventModel.id == query.before,
            CarouselGenerationEventModel.carousel_project_id == query.project_id,
            _project_condition(query.project_id),
        )
    )
    if anchor is None:
        raise InvalidGenerationEventCursorError
    return anchor


async def _run_summaries(
    session: AsyncSession, events: tuple[GenerationEvent, ...], project_id: str
) -> tuple[GenerationRunSummary, ...]:
    run_ids = {event.generation_run_id for event in events}
    if not run_ids:
        return ()
    rows = await session.scalars(
        select(GenerationRunModel)
        .where(
            GenerationRunModel.id.in_(run_ids),
            _project_condition(project_id),
        )
        .order_by(GenerationRunModel.created_at.desc(), GenerationRunModel.id.desc())
    )
    return tuple(_run_summary(row) for row in rows)


def _project_condition(project_id: str) -> ColumnElement[bool]:
    return or_(
        GenerationRunModel.carousel_project_id == project_id,
        and_(
            GenerationRunModel.kind == GenerationKind.AUTOPILOT_DRIVE.value,
            GenerationRunModel.carousel_project_id.is_(None),
            exists(
                select(AutopilotRunModel.id).where(
                    AutopilotRunModel.id
                    == cast(GenerationRunModel.autopilot_run_id, Uuid),
                    AutopilotRunModel.carousel_project_id == project_id,
                )
            ),
        ),
    )


def _event_from_row(row: CarouselGenerationEventModel) -> GenerationEvent:
    return GenerationEvent(
        id=row.id,
        generation_run_id=row.generation_run_id,
        carousel_project_id=row.carousel_project_id,
        kind=GenerationKind(row.kind),
        event_type=row.event_type,
        phase=row.phase,
        outcome=row.outcome,
        occurred_at=row.occurred_at,
        duration_ms=row.duration_ms,
        attempt=row.attempt,
        error_code=row.error_code,
        message_code=row.message_code,
        details=dict[str, object](sanitize_event_details(dict(row.details))),
        langfuse_trace_id=row.langfuse_trace_id,
        langfuse_trace_url=row.langfuse_trace_url,
    )


def _run_summary(row: GenerationRunModel) -> GenerationRunSummary:
    return GenerationRunSummary(
        id=row.id,
        kind=GenerationKind(row.kind),
        status=row.status,
        queued_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
        attempts=row.attempts,
        error_code=row.last_error_code,
    )


__all__ = ["SqlGenerationEventRecorder", "read_generation_log"]
