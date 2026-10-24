"""Hand the queue's pending work back before a revert of the generation worker.

Run once, with the worker stopped, right before the revert deploys. A dashboard
resume the worker never started left its project ``in_progress`` with no run
heartbeat; the reverted web process would refuse a new resume on it forever (the
reaper only alerts on a missing heartbeat). This puts each such project back at
its gate (``awaiting_human``, through the project's write owner) and cancels
every active generation run. Autopilot runs need nothing:
the reverted runner selects them from ``autopilot_runs`` again. Safe to re-run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from sqlalchemy import CursorResult, Update, func, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.editorial.public import CarouselProjectWriteOwner
from rag_backend.modules.generation_queue.constants import (
    ACTIVE_STATUSES,
    KIND_WORKFLOW_RESUME,
    STATUS_CANCELLED,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)


async def _unstarted_projects(session: AsyncSession) -> list[str]:
    queued = select(GenerationRunModel.carousel_project_id).where(
        GenerationRunModel.kind == KIND_WORKFLOW_RESUME,
        GenerationRunModel.status.in_(ACTIVE_STATUSES),
    )
    rows = await session.scalars(
        select(CarouselProjectModel.id).where(
            CarouselProjectModel.phase_status == PHASE_STATUS_IN_PROGRESS,
            CarouselProjectModel.run_heartbeat_at.is_(None),
            CarouselProjectModel.id.in_(queued),
        )
    )
    return [str(project_id) for project_id in rows.all()]


def _cancel_runs() -> Update:
    return (
        update(GenerationRunModel)
        .where(GenerationRunModel.status.in_(ACTIVE_STATUSES))
        .values(status=STATUS_CANCELLED, finished_at=func.now(), updated_at=func.now())
    )


@dataclass(frozen=True)
class RollbackReport:
    """How many projects went back to their gate and runs were cancelled."""

    projects_released: int
    runs_cancelled: int


async def pending(engine: AsyncEngine) -> RollbackReport:
    """What ``hand_back`` would release and cancel, without changing anything."""
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        projects = await _unstarted_projects(session)
        runs = await session.scalar(
            select(func.count()).where(GenerationRunModel.status.in_(ACTIVE_STATUSES))
        )
    return RollbackReport(
        projects_released=len(projects), runs_cancelled=int(runs or 0)
    )


async def hand_back(engine: AsyncEngine) -> RollbackReport:
    """Release unstarted dashboard resumes, then cancel every active run."""
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        projects = await _unstarted_projects(session)
        owner = CarouselProjectWriteOwner(session)
        for project_id in projects:
            await owner.set_phase_status_and_commit(
                project_id, PHASE_STATUS_AWAITING_HUMAN
            )
        cancelled = await session.execute(_cancel_runs())
        await session.commit()
    return RollbackReport(
        projects_released=len(projects),
        runs_cancelled=cast(CursorResult[object], cancelled).rowcount,
    )


__all__ = ["RollbackReport", "hand_back", "pending"]
