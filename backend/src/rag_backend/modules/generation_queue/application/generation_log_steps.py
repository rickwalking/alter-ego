"""Safe notable-step events extracted from workflow results."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from rag_backend.domain.persona_score import lowest_overall, stored_overall
from rag_backend.modules.generation_queue.application.generation_events import (
    record_generation_event,
    set_generation_event_project,
)
from rag_backend.modules.generation_queue.constants import (
    EVENT_CONTENT_GATE,
    EVENT_PERSONA_SCORED,
    EVENT_PHASE_ARTIFACTS,
    EVENT_WORKFLOW_FAILED,
    EVENT_WORKFLOW_SUCCEEDED,
    MESSAGE_GENERATION_FAILED,
    MESSAGE_GENERATION_SUCCEEDED,
    MESSAGE_PHASE_FAILED,
    MESSAGE_PHASE_SUCCEEDED,
    OUTCOME_FAILED,
    OUTCOME_SUCCEEDED,
)
from rag_backend.modules.generation_queue.domain.generation_events import (
    GenerationEventInput,
)

_CONTENT_GATE = "content_gate_validation"
_PERSONA_SCORES = "persona_scores"
_PHASE_STATUS = "phase_status"
_STATUS_FAILED = "failed"
_CONTENT_GATE_BLOCKED = "content_gate_blocked"


class GenerationTrace(Protocol):
    """The trace identity exposed to the generation log."""

    trace_id: str | None
    trace_url: str | None


@dataclass(frozen=True, kw_only=True)
class WorkflowOutcomeObservation:
    """The business outcome, distinct from the queue drive's completion."""

    project_id: str
    phase: str | None
    outcome: str
    error_code: str | None = None
    error_type: str | None = None


async def record_workflow_outcome(observation: WorkflowOutcomeObservation) -> None:
    """Record workflow success or failure without its raw error message."""
    set_generation_event_project(observation.project_id)
    succeeded = observation.outcome == OUTCOME_SUCCEEDED
    details: dict[str, object] = (
        {"error_type": observation.error_type}
        if observation.error_type is not None
        else {}
    )
    await record_generation_event(
        GenerationEventInput(
            event_type=(
                EVENT_WORKFLOW_SUCCEEDED if succeeded else EVENT_WORKFLOW_FAILED
            ),
            outcome=observation.outcome,
            phase=observation.phase,
            error_code=observation.error_code,
            message_code=(
                MESSAGE_GENERATION_SUCCEEDED if succeeded else MESSAGE_GENERATION_FAILED
            ),
            details=details,
        )
    )


async def record_phase_artifacts(
    phase: str, result: dict[str, object], trace: GenerationTrace | None
) -> None:
    """Record a phase result and any safe score/gate summaries it carries."""
    trace_id, trace_url = _trace_identity(trace)
    status = result.get(_PHASE_STATUS)
    outcome = OUTCOME_FAILED if status == _STATUS_FAILED else OUTCOME_SUCCEEDED
    await record_generation_event(
        GenerationEventInput(
            event_type=EVENT_PHASE_ARTIFACTS,
            outcome=outcome,
            phase=phase,
            error_code=status if isinstance(status, str) else None,
            message_code=_message(outcome),
            langfuse_trace_id=trace_id,
            langfuse_trace_url=trace_url,
        )
    )
    scores = result.get(_PERSONA_SCORES)
    if isinstance(scores, Mapping) and scores:
        await _record_persona(phase, scores, trace)
    validation = result.get(_CONTENT_GATE)
    if isinstance(validation, Mapping):
        await _record_gate(phase, validation, trace)


async def _record_persona(
    phase: str, scores: Mapping[object, object], trace: GenerationTrace | None
) -> None:
    trace_id, trace_url = _trace_identity(trace)
    values = list(scores.values())
    scored = sum(stored_overall(entry) is not None for entry in values)
    await record_generation_event(
        GenerationEventInput(
            event_type=EVENT_PERSONA_SCORED,
            outcome=OUTCOME_SUCCEEDED,
            phase=phase,
            message_code=MESSAGE_PHASE_SUCCEEDED,
            details={
                "lowest_score": lowest_overall(scores),
                "scored_count": scored,
                "unscored_count": len(values) - scored,
            },
            langfuse_trace_id=trace_id,
            langfuse_trace_url=trace_url,
        )
    )


async def _record_gate(
    phase: str, validation: Mapping[object, object], trace: GenerationTrace | None
) -> None:
    trace_id, trace_url = _trace_identity(trace)
    violations = validation.get("violations")
    blocking = validation.get("blocking")
    violation_count = len(violations) if isinstance(violations, list) else 0
    blocking_count = (
        len(blocking) if isinstance(blocking, list) else int(bool(blocking))
    )
    failed = (
        bool(blocking_count) or validation.get("validation_status") == _STATUS_FAILED
    )
    outcome = OUTCOME_FAILED if failed else OUTCOME_SUCCEEDED
    await record_generation_event(
        GenerationEventInput(
            event_type=EVENT_CONTENT_GATE,
            outcome=outcome,
            phase=phase,
            error_code=_CONTENT_GATE_BLOCKED if failed else None,
            message_code=_message(outcome),
            details={
                "violation_count": violation_count,
                "blocking_count": blocking_count,
            },
            langfuse_trace_id=trace_id,
            langfuse_trace_url=trace_url,
        )
    )


def _trace_identity(trace: GenerationTrace | None) -> tuple[str | None, str | None]:
    if trace is None:
        return None, None
    return trace.trace_id, trace.trace_url


def _message(outcome: str) -> str:
    return (
        MESSAGE_PHASE_FAILED if outcome == OUTCOME_FAILED else MESSAGE_PHASE_SUCCEEDED
    )


__all__ = [
    "WorkflowOutcomeObservation",
    "record_phase_artifacts",
    "record_workflow_outcome",
]
