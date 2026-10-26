"""Shared read of driven autopilot runs that may still be unstaged."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Row, and_, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.content_mode import (
    CONTENT_MODE_POV,
    CONTENT_MODE_POV_NEWS,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.queue_position import QueueEntry
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.queue_constants import GENERATION_STATUS_QUEUED

_POV_MODES = (CONTENT_MODE_POV, CONTENT_MODE_POV_NEWS)
_NO_MODE = ""
_DRIVEN = (
    AutopilotRunState.QUEUED.value,
    AutopilotRunState.GENERATING.value,
    AutopilotRunState.REWORKING.value,
)


@dataclass(frozen=True, kw_only=True)
class WaitingAutopilotRun:
    """One driven autopilot run with its staging and ordering identity."""

    id: str
    project_id: str | None
    created_at: datetime
    state: str


async def waiting_autopilot_runs(session: AsyncSession) -> list[WaitingAutopilotRun]:
    """Read driven runs oldest first, excluding POV runs awaiting their thesis."""
    run, topic = AutopilotRunModel, TopicCandidateModel
    heading_to_thesis = and_(
        run.state == AutopilotRunState.QUEUED.value,
        run.pov_thesis.is_(None),
        func.coalesce(topic.content_mode, _NO_MODE).in_(_POV_MODES),
    )
    result = await session.execute(
        select(run.id, run.carousel_project_id, run.created_at, run.state)
        .outerjoin(topic, topic.id == run.topic_candidate_id)
        .where(run.state.in_(_DRIVEN), not_(heading_to_thesis))
        .order_by(run.created_at, run.id)
    )
    return [_waiting(row) for row in result.all()]


def waiting_entry(run: WaitingAutopilotRun) -> QueueEntry:
    """Represent unstaged autopilot work in the shared position snapshot."""
    return QueueEntry(
        id=run.id,
        status=GENERATION_STATUS_QUEUED,
        autopilot_run_id=run.id,
        created_at=run.created_at,
        staged=False,
    )


def _waiting(row: Row[tuple[UUID, str | None, datetime, str]]) -> WaitingAutopilotRun:
    return WaitingAutopilotRun(
        id=str(row[0]), project_id=row[1], created_at=row[2], state=row[3]
    )


__all__ = ["WaitingAutopilotRun", "waiting_autopilot_runs", "waiting_entry"]
