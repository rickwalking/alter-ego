"""Settle a drive whose workflow failed: ``dead_letter`` with the cause.

The resume runner swallows a phase failure on purpose: it has already marked the
project failed, published ``run.finished(failed)`` and, for autopilot, the run has
escalated. So the drive ends ``DONE`` and the run must not be marked ``succeeded``.
It moves to the existing ``dead_letter`` status with ``workflow_failed`` and the
safe cause, and no owner notice is staged again.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from rag_backend.modules.generation_queue.application.generation_events import (
    current_generation_event_project,
    record_generation_event,
)
from rag_backend.modules.generation_queue.application.job_tracker import (
    _Attempt,
    _Tracker,
)
from rag_backend.modules.generation_queue.constants import (
    ERROR_MESSAGE_MAX_CHARS,
    ERROR_WORKFLOW_FAILED,
    EVENT_RUN_DEAD_LETTER,
    LOG_WORKFLOW_FAILED,
    MESSAGE_GENERATION_FAILED,
    OUTCOME_DEAD_LETTER,
)
from rag_backend.modules.generation_queue.domain.generation_events import (
    GenerationEventInput,
)
from rag_backend.modules.generation_queue.domain.models import (
    AttemptDeadLetterCommand,
)

if TYPE_CHECKING:
    from rag_backend.modules.generation_queue.application.job_handler import (
        HandlerDependencies,
    )

logger = structlog.get_logger()


@dataclass(frozen=True)
class FailedDrive:
    """The attempt whose drive ended after its workflow failed, and why."""

    attempt: _Attempt
    tracker: _Tracker
    cause: str


async def settle_workflow_failure(
    deps: HandlerDependencies, failed: FailedDrive
) -> None:
    """Dead-letter the attempt with the cause; skipped when it lost its fence."""
    run_id = failed.attempt.run.id
    moved = await deps.store.mark_attempt_dead_letter(
        AttemptDeadLetterCommand(
            run_id=run_id,
            attempt_id=failed.attempt.attempt_id,
            error_code=ERROR_WORKFLOW_FAILED,
            error=failed.cause[:ERROR_MESSAGE_MAX_CHARS],
        )
    )
    if not moved:
        return
    await failed.tracker.fail(ERROR_WORKFLOW_FAILED)
    await record_generation_event(
        GenerationEventInput(
            event_type=EVENT_RUN_DEAD_LETTER,
            outcome=OUTCOME_DEAD_LETTER,
            occurred_at=deps.clock.now(),
            error_code=ERROR_WORKFLOW_FAILED,
            message_code=MESSAGE_GENERATION_FAILED,
        )
    )
    logger.warning(LOG_WORKFLOW_FAILED, generation_run_id=str(run_id))
    project_id = current_generation_event_project()
    if project_id is not None:
        await deps.completion.completed(project_id, succeeded=False)


__all__ = ["FailedDrive", "settle_workflow_failure"]
