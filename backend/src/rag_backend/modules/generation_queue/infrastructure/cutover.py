"""Find carousel projects a dead driver left ``in_progress`` with nothing queued.

At the cutover to the worker, a dashboard resume the old web process was running
when the deploy stopped it has no ``generation_runs`` row; afterwards, a
synchronous dashboard start a deploy kills is in the same state. Autopilot
projects are left out: the dispatcher stages their run from ``autopilot_runs``
and the drive recovers them.
"""

from __future__ import annotations

from sqlalchemy import column, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.generation_queue.constants import (
    ACTIVE_STATUSES,
    COLUMN_CAROUSEL_PROJECT_ID,
    TABLE_AUTOPILOT_RUNS,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)

_AUTOPILOT_RUNS = table(TABLE_AUTOPILOT_RUNS, column(COLUMN_CAROUSEL_PROJECT_ID))


async def orphaned_projects(session: AsyncSession) -> list[tuple[str, str]]:
    """``(project id, title)`` of each orphan, oldest update first."""
    queued = select(GenerationRunModel.carousel_project_id).where(
        GenerationRunModel.status.in_(ACTIVE_STATUSES),
        GenerationRunModel.carousel_project_id.is_not(None),
    )
    autopilot = select(_AUTOPILOT_RUNS.c.carousel_project_id).where(
        _AUTOPILOT_RUNS.c.carousel_project_id.is_not(None)
    )
    rows = await session.execute(
        select(CarouselProjectModel.id, CarouselProjectModel.title)
        .where(
            CarouselProjectModel.phase_status == PHASE_STATUS_IN_PROGRESS,
            CarouselProjectModel.id.not_in(queued),
            CarouselProjectModel.id.not_in(autopilot),
        )
        .order_by(CarouselProjectModel.updated_at)
    )
    return [(str(project_id), title or "") for project_id, title in rows.all()]


__all__ = ["orphaned_projects"]
