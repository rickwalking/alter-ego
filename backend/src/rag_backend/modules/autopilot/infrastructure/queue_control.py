"""``QueueControl`` on the webhook's session, through the generation queue facade.

The generation queue facade is imported inside the methods: that package imports
the autopilot queue bridge at load time, so a module-level import here would make
the two packages load each other.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.content_mode import (
    CONTENT_MODE_POV,
    CONTENT_MODE_POV_NEWS,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.queue_position import QueueSnapshot
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.queue_constants import RECENT_DRIVES

_POV_MODES = (CONTENT_MODE_POV, CONTENT_MODE_POV_NEWS)
_NO_MODE = ""
_DRIVEN = (
    AutopilotRunState.QUEUED.value,
    AutopilotRunState.GENERATING.value,
    AutopilotRunState.REWORKING.value,
)


class SqlQueueControl:
    """Implements ``QueueControl``; nothing here commits."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def snapshot(self) -> QueueSnapshot:
        """Active generation runs first, then driven runs not picked up yet.

        A POV run still ``queued`` without a confirmed thesis is left out: its
        first step only moves it to ``awaiting_thesis``.
        """
        from rag_backend.modules.generation_queue.public import (
            active_queue,
            recent_drive_minutes,
        )

        active = await active_queue(self._session)
        ahead = tuple(work.autopilot_run_id for work in active)
        staged = {run_id for run_id in ahead if run_id is not None}
        run, topic = AutopilotRunModel, TopicCandidateModel
        heading_to_thesis = and_(
            run.state == AutopilotRunState.QUEUED.value,
            run.pov_thesis.is_(None),
            func.coalesce(topic.content_mode, _NO_MODE).in_(_POV_MODES),
        )
        result = await self._session.execute(
            select(run.id)
            .outerjoin(topic, topic.id == run.topic_candidate_id)
            .where(run.state.in_(_DRIVEN), not_(heading_to_thesis))
            .order_by(run.created_at, run.id)
        )
        waiting = tuple(
            str(row[0]) for row in result.all() if str(row[0]) not in staged
        )
        drives = await recent_drive_minutes(self._session, RECENT_DRIVES)
        return QueueSnapshot(ahead=ahead, waiting=waiting, drive_minutes=tuple(drives))

    async def requeue_dead_letter(self, run_id: UUID) -> bool:
        """Requeue the run's latest dead letter in this transaction."""
        from rag_backend.modules.generation_queue.public import (
            requeue_autopilot_dead_letter,
        )

        return await requeue_autopilot_dead_letter(self._session, str(run_id))


__all__ = ["SqlQueueControl"]
