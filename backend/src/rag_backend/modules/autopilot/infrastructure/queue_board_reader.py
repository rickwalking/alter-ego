"""``QueueBoardReader`` on the request's session, through the generation queue facade.

The facade is imported inside the methods: that package imports the autopilot
queue bridge at load time. Nothing here commits.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.application.queue_board_service import (
    GenerationFacts,
)
from rag_backend.modules.autopilot.domain.queue_board import (
    AutopilotFacts,
    GenerationRow,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.queue_constants import RECENT_DRIVES


class SqlQueueBoardReader:
    """Implements ``QueueBoardReader``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def rows(self) -> list[GenerationRow]:
        """Active runs in FIFO order, then the recent dead letters."""
        from rag_backend.modules.generation_queue.public import queue_board_rows

        return [
            GenerationRow(
                id=str(row.id),
                kind=row.kind,
                status=row.status,
                autopilot_run_id=row.autopilot_run_id,
                carousel_project_id=row.carousel_project_id,
                title=row.title,
                last_phase=row.last_phase,
                last_error_code=row.last_error_code,
                created_at=row.created_at,
                started_at=row.started_at,
                next_attempt_at=row.next_attempt_at,
                finished_at=row.finished_at,
                superseded=row.superseded,
            )
            for row in await queue_board_rows(self._session)
        ]

    async def facts(self, run_ids: tuple[str, ...]) -> dict[str, AutopilotFacts]:
        """Title and current reason of each autopilot run."""
        if not run_ids:
            return {}
        run, topic = AutopilotRunModel, TopicCandidateModel
        result = await self._session.execute(
            select(run.id, topic.title, run.state, run.state_reason)
            .join(topic, topic.id == run.topic_candidate_id)
            .where(run.id.in_([UUID(run_id) for run_id in run_ids]))
        )
        return {
            str(run_id): AutopilotFacts(title=title, state=state, state_reason=reason)
            for run_id, title, state, reason in result.all()
        }

    async def drive_minutes(self) -> list[float]:
        """How long the latest finished drives took."""
        from rag_backend.modules.generation_queue.public import recent_drive_minutes

        return await recent_drive_minutes(self._session, RECENT_DRIVES)

    async def generation(self, run_id: UUID) -> GenerationFacts | None:
        """One generation run's facts, or None."""
        from rag_backend.modules.generation_queue.public import generation_run_facts

        facts = await generation_run_facts(self._session, run_id)
        if facts is None:
            return None
        return GenerationFacts(
            kind=facts.kind,
            status=facts.status,
            autopilot_run_id=facts.autopilot_run_id,
        )

    async def theme_exists(self, candidate_id: UUID) -> bool:
        """True when the topic candidate exists."""
        found = await self._session.get(TopicCandidateModel, candidate_id)
        return found is not None

    async def cancel(self, run_id: UUID) -> bool:
        """Cancel a queued or retry-waiting run (compare-and-set)."""
        from rag_backend.modules.generation_queue.public import cancel_queued_run

        return await cancel_queued_run(self._session, run_id)


__all__ = ["SqlQueueBoardReader"]
