"""What a dead-lettered generation run tells Pedro.

An autopilot run is parked the way an engine error parks it (``escalated``, or
``failed`` before it started), with the queue's reason: the state change writes the
outbox row the Telegram dispatcher already turns into exactly one owner message.
A dashboard resume marks its project ``failed`` and publishes the run's end, so
the open editor shows the error and the Retry button.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.editorial_workflow_run_events import (
    publish_run_finished,
)
from rag_backend.domain.constants.carousel_run import RUN_FINISHED_REASON_FAILED
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_FAILED
from rag_backend.modules.autopilot.queue_bridge import AutopilotQueueBridge
from rag_backend.modules.editorial.public import CarouselProjectWriteOwner
from rag_backend.modules.generation_queue.domain.models import (
    GenerationKind,
    GenerationRun,
)
from rag_backend.modules.generation_queue.infrastructure.drive_adapters import (
    SessionFactory,
)

REASON_DEAD_LETTER = "queue_dead_letter:{code}"


class OwnerDeadLetterNotices:
    """Implements ``DeadLetterNotices``."""

    def __init__(self, bridge: AutopilotQueueBridge, sessions: SessionFactory) -> None:
        self._bridge = bridge
        self._sessions = sessions

    async def stage(self, run: GenerationRun, error_code: str) -> None:
        """Park the autopilot run, or fail the dashboard project, with the reason."""
        if run.kind is GenerationKind.AUTOPILOT_DRIVE and run.autopilot_run_id:
            await self._bridge.park(
                run.autopilot_run_id, REASON_DEAD_LETTER.format(code=error_code)
            )
            return
        if run.carousel_project_id:
            await self._fail_project(run.carousel_project_id)

    async def _fail_project(self, project_id: str) -> None:
        async with self._sessions() as session:
            await CarouselProjectWriteOwner(session).set_phase_status_and_commit(
                project_id, PHASE_STATUS_FAILED
            )
        await publish_run_finished(
            project_id,
            RUN_FINISHED_REASON_FAILED,
            final_phase_status=PHASE_STATUS_FAILED,
        )


__all__ = ["REASON_DEAD_LETTER", "OwnerDeadLetterNotices"]
