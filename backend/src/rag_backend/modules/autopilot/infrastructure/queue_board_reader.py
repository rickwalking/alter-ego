"""SQL panel reader combining generation rows and shared unstaged autopilot work."""

from __future__ import annotations

from typing import TYPE_CHECKING
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
from rag_backend.modules.autopilot.infrastructure.queue_board_projects import (
    QueueBoardProjects,
)
from rag_backend.modules.autopilot.infrastructure.queue_board_recovery import (
    enrich_recovery,
)
from rag_backend.modules.autopilot.infrastructure.queue_waiting import (
    WaitingAutopilotRun,
    waiting_autopilot_runs,
)
from rag_backend.modules.autopilot.queue_constants import (
    GENERATION_KIND_AUTOPILOT,
    GENERATION_STATUS_DEAD,
    GENERATION_STATUS_QUEUED,
    RECENT_DRIVES,
)

if TYPE_CHECKING:
    from rag_backend.modules.generation_queue.infrastructure.queue_board import BoardRow


class SqlQueueBoardReader:
    """Implements ``QueueBoardReader`` without committing request state."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def rows(self) -> list[GenerationRow]:
        """Return staged rows plus unstaged driven runs, deduped for staging races."""
        from rag_backend.modules.generation_queue.public import queue_board_rows

        driven = await waiting_autopilot_runs(self._session)
        stored = await queue_board_rows(self._session)
        generation = [_generation_row(row) for row in stored]
        staged = {
            row.autopilot_run_id
            for row in generation
            if row.status != GENERATION_STATUS_DEAD and row.autopilot_run_id is not None
        }
        unstaged = (_synthetic(run) for run in driven if run.id not in staged)
        rows = [*generation, *unstaged]
        attributed = await QueueBoardProjects(self._session).enrich(rows)
        return await enrich_recovery(self._session, attributed)

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


def _generation_row(row: BoardRow) -> GenerationRow:
    return GenerationRow(
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
        pgq_job_id=row.pgq_job_id,
        priority=row.priority,
        superseded=row.superseded,
    )


def _synthetic(run: WaitingAutopilotRun) -> GenerationRow:
    return GenerationRow(
        id=run.id,
        kind=GENERATION_KIND_AUTOPILOT,
        status=GENERATION_STATUS_QUEUED,
        autopilot_run_id=run.id,
        carousel_project_id=run.project_id,
        title="",
        last_phase=None,
        last_error_code=None,
        created_at=run.created_at,
        finished_at=None,
        staged=False,
    )


__all__ = ["SqlQueueBoardReader"]
