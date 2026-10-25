"""What the dashboard's queue panel reads and changes, in the caller's session.

The panel lists the active generation runs (queued, running, waiting for a retry)
in FIFO order and the dead letters of the last 7 days. A queued or retry-waiting
run can be cancelled with a compare-and-set; a running one cannot (it would cut a
phase in half).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.generation_queue.constants import (
    ACTIVE_STATUSES,
    SCAN_RECOVERY_DAYS,
    STATUS_CANCELLED,
    STATUS_DEAD_LETTER,
    STATUS_QUEUED,
    STATUS_RETRY_WAIT,
)
from rag_backend.modules.generation_queue.domain.clock import UTC_CLOCK
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)

_G = GenerationRunModel
_TITLE_KEY = "project_title"
_CANCELLABLE = (STATUS_QUEUED, STATUS_RETRY_WAIT)


@dataclass(frozen=True, kw_only=True)
class BoardRow:
    """One generation run as the panel shows it."""

    id: UUID
    kind: str
    status: str
    autopilot_run_id: str | None
    carousel_project_id: str | None
    title: str
    last_phase: str | None
    last_error_code: str | None
    last_error: str | None
    created_at: datetime
    started_at: datetime | None
    next_attempt_at: datetime | None
    finished_at: datetime | None
    pgq_job_id: int | None
    superseded: bool


@dataclass(frozen=True, kw_only=True)
class RunFacts:
    """Kind, status and autopilot run of one generation run."""

    kind: str
    status: str
    autopilot_run_id: str | None


async def board_rows(session: AsyncSession) -> list[BoardRow]:
    """Active runs in the worker's order, then the dead letters of the last 7 days.

    The worker takes PgQueuer jobs in job order, so handed-over runs come first by
    job id, then runs not handed over yet by creation. A dead letter is
    ``superseded`` when a later run exists for the same project (the editor
    resumed it).
    """
    since = UTC_CLOCK.now() - timedelta(days=SCAN_RECOVERY_DAYS)
    result = await session.execute(
        select(_G)
        .where(
            or_(
                _G.status.in_(ACTIVE_STATUSES),
                (_G.status == STATUS_DEAD_LETTER) & (_G.finished_at >= since),
            )
        )
        .order_by(_G.pgq_job_id.is_(None), _G.pgq_job_id, _G.created_at, _G.id)
    )
    models = list(result.scalars().all())
    latest = await _latest_by_project(session, models)
    return [_row(model, latest) for model in models]


async def _latest_by_project(
    session: AsyncSession, models: list[GenerationRunModel]
) -> dict[str, datetime]:
    projects = {
        m.carousel_project_id
        for m in models
        if m.status == STATUS_DEAD_LETTER and m.carousel_project_id
    }
    if not projects:
        return {}
    result = await session.execute(
        select(_G.carousel_project_id, func.max(_G.created_at))
        .where(_G.carousel_project_id.in_(projects))
        .group_by(_G.carousel_project_id)
    )
    return {str(project): created for project, created in result.all()}


async def run_facts(session: AsyncSession, run_id: UUID) -> RunFacts | None:
    """The run's kind, status and autopilot run, or None when it does not exist."""
    model = await session.get(_G, run_id)
    if model is None:
        return None
    return RunFacts(
        kind=model.kind, status=model.status, autopilot_run_id=model.autopilot_run_id
    )


async def cancel_queued(session: AsyncSession, run_id: UUID) -> bool:
    """Queued or retry-waiting → cancelled (compare-and-set); no commit."""
    result = await session.execute(
        update(_G)
        .where(_G.id == run_id, _G.status.in_(_CANCELLABLE))
        .values(status=STATUS_CANCELLED, finished_at=UTC_CLOCK.now())
    )
    return cast(CursorResult[object], result).rowcount == 1


def _row(model: GenerationRunModel, latest: dict[str, datetime]) -> BoardRow:
    payload = model.payload or {}
    newest = latest.get(model.carousel_project_id or "")
    return BoardRow(
        id=model.id,
        kind=model.kind,
        status=model.status,
        autopilot_run_id=model.autopilot_run_id,
        carousel_project_id=model.carousel_project_id,
        title=str(payload.get(_TITLE_KEY) or ""),
        last_phase=model.last_phase,
        last_error_code=model.last_error_code,
        last_error=model.last_error,
        created_at=model.created_at,
        started_at=model.started_at,
        next_attempt_at=model.next_attempt_at,
        finished_at=model.finished_at,
        pgq_job_id=model.pgq_job_id,
        superseded=newest is not None and newest > model.created_at,
    )


__all__ = ["BoardRow", "RunFacts", "board_rows", "cancel_queued", "run_facts"]
