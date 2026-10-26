"""``QueueControl`` on the webhook's session, through the generation queue facade.

The generation queue facade is imported inside the methods: that package imports
the autopilot queue bridge at load time, so a module-level import here would make
the two packages load each other.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
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
from rag_backend.modules.autopilot.queue_constants import (
    GENERATION_KIND_AUTOPILOT,
    OUTCOME_ALREADY,
    OUTCOME_DONE,
    OUTCOME_NOT_ALLOWED,
    OUTCOME_NOT_FOUND,
    RECENT_DRIVES,
)

if TYPE_CHECKING:
    from rag_backend.modules.generation_queue.domain.manual_recovery import (
        ManualReprocessCommand,
        RecoveryResult,
    )
    from rag_backend.modules.generation_queue.domain.manual_recovery_ports import (
        MaintenanceNotifier,
    )

_POV_MODES = (CONTENT_MODE_POV, CONTENT_MODE_POV_NEWS)
_NO_MODE = ""
_DRIVEN = (
    AutopilotRunState.QUEUED.value,
    AutopilotRunState.GENERATING.value,
    AutopilotRunState.REWORKING.value,
)


class SqlQueueControl:
    """Bind queue reads and shared recovery to one request session."""

    def __init__(
        self, session: AsyncSession, notifier: MaintenanceNotifier | None = None
    ) -> None:
        self._session = session
        self._notifier = notifier

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

    async def reprocess_autopilot(self, run_id: UUID, actor_id: str) -> UUID | None:
        """Delegate Telegram retry to shared manual recovery semantics."""
        from rag_backend.modules.generation_queue.domain.manual_recovery import (
            ManualReprocessCommand,
            RecoveryOutcome,
        )

        command = ManualReprocessCommand(
            project_id=None, run_id=None, autopilot_run_id=run_id, actor_id=actor_id
        )
        result = await self._recover(command)
        if result.outcome is not RecoveryOutcome.QUEUED or result.run is None:
            return None
        queued = result.run.autopilot_run_id
        return UUID(queued) if queued is not None else None

    async def retry_generation(self, run_id: UUID, actor_id: str) -> str:
        """Preserve the panel outcome contract around shared manual recovery."""
        from rag_backend.modules.generation_queue.domain.manual_recovery import (
            ManualReprocessCommand,
        )
        from rag_backend.modules.generation_queue.public import generation_run_facts

        facts = await generation_run_facts(self._session, run_id)
        if facts is None:
            return OUTCOME_NOT_FOUND
        if facts.kind != GENERATION_KIND_AUTOPILOT:
            return OUTCOME_NOT_ALLOWED
        command = ManualReprocessCommand(
            project_id=None, run_id=run_id, actor_id=actor_id
        )
        return _retry_outcome(await self._recover(command))

    async def _recover(self, command: ManualReprocessCommand) -> RecoveryResult:
        from rag_backend.modules.generation_queue.public import build_manual_recovery

        service = build_manual_recovery(self._session, self._notifier)
        return await service.reprocess(command)

    async def requeue_dead_letter(self, run_id: UUID) -> bool:
        """Requeue the run's latest dead letter in this transaction."""
        from rag_backend.modules.generation_queue.public import (
            requeue_autopilot_dead_letter,
        )

        return await requeue_autopilot_dead_letter(self._session, str(run_id))


def _retry_outcome(result: RecoveryResult) -> str:
    from rag_backend.modules.generation_queue.domain.manual_recovery import (
        RecoveryOutcome,
        RefusalCode,
    )

    if result.outcome is RecoveryOutcome.QUEUED:
        return OUTCOME_DONE
    if result.outcome is RecoveryOutcome.NOT_FOUND:
        return OUTCOME_NOT_FOUND
    if result.refusal is RefusalCode.UNSUPPORTED:
        return OUTCOME_NOT_ALLOWED
    return OUTCOME_ALREADY


__all__ = ["SqlQueueControl"]
