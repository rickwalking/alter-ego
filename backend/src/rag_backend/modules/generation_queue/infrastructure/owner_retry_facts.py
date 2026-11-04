"""Gather the facts of an owner Retry on the request's session.

Lock order, the same as the 72-hour escalation close (run, then carousel): the
carousel's autopilot run row is read ``FOR UPDATE`` first, then the carousel row
through the editorial write owner, so a second Retry waits for the first and
then reads its ``in_progress``. The checkpoint, the generation queue and the
artifact lock are read after both locks are held.
"""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    DEFAULT_REVISION_CAP_PER_PHASE,
    PHASE_STATUS_AWAITING_HUMAN,
)
from rag_backend.domain.persona_score import lowest_overall
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.editorial.public import (
    CarouselProjectWriteOwner,
    EditorialWorkflowEngine,
    RetryRow,
    content_approve_blocker,
    is_carousel_project_lock_held_session,
)
from rag_backend.modules.generation_queue.constants import STATUS_DEAD_LETTER
from rag_backend.modules.generation_queue.domain.owner_retry import (
    AutopilotFacts,
    CarouselRetryState,
    CheckpointFacts,
    OwnerRetryCommand,
    QueueFacts,
    RetryFacts,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.run_fences import (
    project_has_active_run,
)

_PERSONA_SCORES_KEY = "persona_scores"


class OwnerRetryFacts:
    """Read the carousel under its lock, then everything a Retry decides on."""

    def __init__(self, session: AsyncSession, engine: EditorialWorkflowEngine) -> None:
        self._session = session
        self._engine = engine

    async def read(self, command: OwnerRetryCommand) -> RetryFacts | None:
        """None when the carousel is missing."""
        autopilot = await self._lock_autopilot(command.project_id)
        owner = CarouselProjectWriteOwner(self._session)
        row = await owner.lock_for_retry(command.project_id)
        if row is None:
            return None
        return RetryFacts(
            actor_id=command.actor_id,
            carousel=_carousel(row),
            checkpoint=await self._checkpoint(row),
            queue=await self._queue(row.project_id, autopilot),
            autopilot=autopilot,
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
            revise_capped=_revise_capped(state),
        )

    async def _queue(
        self, project_id: str, autopilot: AutopilotFacts | None
    ) -> QueueFacts:
        active = await self._session.scalar(
            select(project_has_active_run(literal(project_id)))
        )
        return QueueFacts(
            active_run=bool(active),
            latest_dead_letter=await self._latest_dead(project_id, autopilot),
            mutation_locked=await is_carousel_project_lock_held_session(
                self._session, project_id
            ),
        )

    async def _latest_dead(
        self, project_id: str, autopilot: AutopilotFacts | None
    ) -> bool:
        """True when the newest generation run of the carousel dead-lettered."""
        scope = GenerationRunModel.carousel_project_id == project_id
        if autopilot is not None:
            scope = or_(
                scope, GenerationRunModel.autopilot_run_id == str(autopilot.run_id)
            )
        latest = await self._session.scalar(
            select(GenerationRunModel.status)
            .where(scope)
            .order_by(
                GenerationRunModel.created_at.desc(), GenerationRunModel.id.desc()
            )
            .limit(1)
        )
        return latest == STATUS_DEAD_LETTER

    async def _lock_autopilot(self, project_id: str) -> AutopilotFacts | None:
        row = (
            await self._session.execute(
                select(
                    AutopilotRunModel.id,
                    AutopilotRunModel.state,
                    AutopilotRunModel.state_reason,
                )
                .where(AutopilotRunModel.carousel_project_id == project_id)
                .with_for_update()
            )
        ).one_or_none()
        if row is None:
            return None
        return AutopilotFacts(run_id=row[0], state=str(row[1]), reason=row[2])


def _revise_capped(state: CarouselWorkflowState) -> bool:
    """A plain revise of the current phase would exceed the revision cap."""
    from rag_backend.application.services.carousel import (
        editorial_workflow_service_helpers as engine_checks,
    )

    phase = engine_checks.resolve_revision_cap_phase(state, None)
    if phase is None:
        return False
    counts = state.get("revision_count") or {}
    used = int(counts.get(phase, 0)) if isinstance(counts, dict) else 0
    return used >= DEFAULT_REVISION_CAP_PER_PHASE


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
