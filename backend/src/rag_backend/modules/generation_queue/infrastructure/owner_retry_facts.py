"""Gather the facts of an owner Retry on the request's session.

The carousel row is read ``FOR UPDATE`` through the editorial write owner, so a
second Retry waits for the first and then reads its ``in_progress``. The
checkpoint, the autopilot run, the generation queue and the artifact lock are
read after the lock is held.
"""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import ColumnElement, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_AWAITING_HUMAN,
)
from rag_backend.domain.persona_score import lowest_overall
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.editorial.public import (
    CarouselProjectWriteOwner,
    EditorialWorkflowEngine,
    RetryRow,
    content_approve_blocker,
    is_carousel_project_lock_held_session,
)
from rag_backend.modules.generation_queue.domain.owner_retry import (
    AutopilotFacts,
    CarouselRetryState,
    CheckpointFacts,
    OwnerRetryCommand,
    QueueFacts,
    RetryFacts,
)
from rag_backend.modules.generation_queue.infrastructure.run_fences import (
    project_has_active_run,
    project_has_held_run,
)

_PERSONA_SCORES_KEY = "persona_scores"


class OwnerRetryFacts:
    """Read the carousel under its lock, then everything a Retry decides on."""

    def __init__(self, session: AsyncSession, engine: EditorialWorkflowEngine) -> None:
        self._session = session
        self._engine = engine

    async def read(self, command: OwnerRetryCommand) -> RetryFacts | None:
        """None when the carousel is missing."""
        owner = CarouselProjectWriteOwner(self._session)
        row = await owner.lock_for_retry(command.project_id)
        if row is None:
            return None
        return RetryFacts(
            actor_id=command.actor_id,
            carousel=_carousel(row),
            checkpoint=await self._checkpoint(row),
            queue=await self._queue(row.project_id),
            autopilot=await self._autopilot(row.project_id),
        )

    async def _checkpoint(self, row: RetryRow) -> CheckpointFacts:
        state = await self._engine.get_workflow_state(row.project_id)
        if state is None:
            return CheckpointFacts(present=False)
        snapshot: Mapping[str, object] = dict(state)
        blocker = None
        if row.phase_status == PHASE_STATUS_AWAITING_HUMAN:
            blocker = content_approve_blocker(snapshot)
        return CheckpointFacts(
            present=True,
            parked=await self._engine.is_parked_before_node(row.project_id),
            blocker=blocker,
            persona_score=lowest_overall(snapshot.get(_PERSONA_SCORES_KEY)),
        )

    async def _queue(self, project_id: str) -> QueueFacts:
        return QueueFacts(
            active_run=await self._exists(project_has_active_run(literal(project_id))),
            held_run=await self._exists(project_has_held_run(literal(project_id))),
            mutation_locked=await is_carousel_project_lock_held_session(
                self._session, project_id
            ),
        )

    async def _exists(self, clause: ColumnElement[bool]) -> bool:
        return bool(await self._session.scalar(select(clause)))

    async def _autopilot(self, project_id: str) -> AutopilotFacts | None:
        run = await SqlAlchemyAutopilotRepository(self._session).find_by_carousel(
            project_id
        )
        if run is None:
            return None
        return AutopilotFacts(
            run_id=run.run_id,
            state=run.state.value,
            reason=run.state_reason,
        )


def _carousel(row: RetryRow) -> CarouselRetryState:
    return CarouselRetryState(
        owner_id=row.owner_id,
        assigned_reviewer_id=row.assigned_reviewer_id,
        topic=row.topic,
        phase=row.current_phase,
        phase_status=row.phase_status,
        status=row.status,
        workflow_status=row.workflow_status,
        lock_version=row.lock_version,
    )


__all__ = ["OwnerRetryFacts"]
