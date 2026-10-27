"""Public generation-event contracts of the generation queue bounded context."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.generation_queue.application.generation_events import (
    record_generation_event,
    set_generation_event_project,
)
from rag_backend.modules.generation_queue.application.generation_log_steps import (
    WorkflowOutcomeObservation,
    record_phase_artifacts,
    record_workflow_outcome,
)
from rag_backend.modules.generation_queue.constants import (
    EVENT_CONTENT_GATE,
    EVENT_IMAGE_JOB_FAILED,
    EVENT_IMAGE_JOB_REUSED,
    EVENT_IMAGE_JOB_STARTED,
    EVENT_IMAGE_JOB_SUCCEEDED,
    EVENT_IMAGE_REUSED,
    EVENT_IMAGE_SLIDE_FAILED,
    EVENT_IMAGE_SLIDE_SUCCEEDED,
    EVENT_PDF_FAILED,
    EVENT_PDF_SUCCEEDED,
    EVENT_PERSONA_SCORED,
    EVENT_PHASE_ARTIFACTS,
    EVENT_RECOVERY_REAPED,
    EVENT_RUN_DEAD_LETTER,
    EVENT_RUN_LOST,
    EVENT_RUN_QUEUED,
    EVENT_WORKFLOW_FAILED,
    EVENT_WORKFLOW_SUCCEEDED,
    MESSAGE_EXPORT,
    MESSAGE_GENERATION_FAILED,
    MESSAGE_GENERATION_QUEUED,
    MESSAGE_GENERATION_RETRY,
    MESSAGE_GENERATION_SUCCEEDED,
    MESSAGE_IMAGE_JOB,
    MESSAGE_PHASE_FAILED,
    MESSAGE_PHASE_SUCCEEDED,
    MESSAGE_RECOVERED,
    OUTCOME_DEAD_LETTER,
    OUTCOME_FAILED,
    OUTCOME_QUEUED,
    OUTCOME_RECOVERED,
    OUTCOME_REUSED,
    OUTCOME_RUNNING,
    OUTCOME_SUCCEEDED,
    OUTCOME_WARNING,
)
from rag_backend.modules.generation_queue.domain.generation_events import (
    EventDetail,
    GenerationEventInput,
    GenerationEventRun,
    GenerationLogPage,
    GenerationLogQuery,
    InvalidGenerationEventCursorError,
)

__all__ = [
    "EVENT_CONTENT_GATE",
    "EVENT_IMAGE_JOB_FAILED",
    "EVENT_IMAGE_JOB_REUSED",
    "EVENT_IMAGE_JOB_STARTED",
    "EVENT_IMAGE_JOB_SUCCEEDED",
    "EVENT_IMAGE_REUSED",
    "EVENT_IMAGE_SLIDE_FAILED",
    "EVENT_IMAGE_SLIDE_SUCCEEDED",
    "EVENT_PDF_FAILED",
    "EVENT_PDF_SUCCEEDED",
    "EVENT_PERSONA_SCORED",
    "EVENT_PHASE_ARTIFACTS",
    "EVENT_RECOVERY_REAPED",
    "EVENT_RUN_DEAD_LETTER",
    "EVENT_RUN_LOST",
    "EVENT_RUN_QUEUED",
    "EVENT_WORKFLOW_FAILED",
    "EVENT_WORKFLOW_SUCCEEDED",
    "MESSAGE_EXPORT",
    "MESSAGE_GENERATION_FAILED",
    "MESSAGE_GENERATION_QUEUED",
    "MESSAGE_GENERATION_RETRY",
    "MESSAGE_GENERATION_SUCCEEDED",
    "MESSAGE_IMAGE_JOB",
    "MESSAGE_PHASE_FAILED",
    "MESSAGE_PHASE_SUCCEEDED",
    "MESSAGE_RECOVERED",
    "OUTCOME_DEAD_LETTER",
    "OUTCOME_FAILED",
    "OUTCOME_QUEUED",
    "OUTCOME_RECOVERED",
    "OUTCOME_REUSED",
    "OUTCOME_RUNNING",
    "OUTCOME_SUCCEEDED",
    "OUTCOME_WARNING",
    "EventDetail",
    "GenerationEventInput",
    "GenerationEventRun",
    "GenerationLogPage",
    "GenerationLogQuery",
    "InvalidGenerationEventCursorError",
    "WorkflowOutcomeObservation",
    "read_generation_log",
    "record_generation_event",
    "record_phase_artifacts",
    "record_workflow_outcome",
    "set_generation_event_project",
]


async def read_generation_log(
    session: AsyncSession, query: GenerationLogQuery
) -> GenerationLogPage:
    """Read one authorized carousel's bounded generation-event page."""
    from rag_backend.modules.generation_queue.infrastructure.generation_events import (
        read_generation_log as read_page,
    )

    return await read_page(session, query)
