"""SSE publish functions for editorial workflow."""

from __future__ import annotations

from rag_backend.application.services.carousel.editorial_workflow_sse_build import (
    build_artifact_event,
    build_error_event,
    build_phase_change_event,
    build_progress_event,
    build_review_gate_payload,
    build_review_required_event,
    resolve_workflow_sse_error_message,
)
from rag_backend.application.services.carousel.editorial_workflow_sse_constants import (
    WORKFLOW_ARTIFACT_UPDATE_FIELD_MAP,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
)


async def publish_workflow_phase_change(
    project_id: str,
    phase: str,
    phase_status: str,
) -> None:
    """Broadcast a phase_change event to workflow SSE subscribers."""
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        get_workflow_sse_hub,
    )

    await get_workflow_sse_hub().publish(
        project_id,
        build_phase_change_event(project_id, phase, phase_status),
    )


async def publish_workflow_progress(
    project_id: str,
    phase: str,
    phase_progress: dict[str, object],
) -> None:
    """Broadcast a progress event to workflow SSE subscribers."""
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        get_workflow_sse_hub,
    )

    await get_workflow_sse_hub().publish(
        project_id,
        build_progress_event(project_id, phase, phase_progress),
    )


async def publish_workflow_review_required(
    project_id: str,
    state: CarouselWorkflowState,
) -> None:
    """Broadcast a review_required event with gate payload."""
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        get_workflow_sse_hub,
    )

    phase = str(state.get("current_phase", ""))
    phase_status = str(state.get("phase_status", ""))
    await get_workflow_sse_hub().publish(
        project_id,
        build_review_required_event(
            project_id,
            phase,
            phase_status,
            build_review_gate_payload(state),
        ),
    )


async def publish_workflow_artifact(
    project_id: str,
    phase: str,
    artifact_type: str,
    data: object,
) -> None:
    """Broadcast an incremental artifact update to workflow SSE subscribers."""
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        get_workflow_sse_hub,
    )

    await get_workflow_sse_hub().publish(
        project_id,
        build_artifact_event(project_id, phase, artifact_type, data),
    )


async def publish_workflow_artifacts_from_updates(
    project_id: str,
    phase: str,
    updates: dict[str, object],
) -> None:
    """Publish artifact SSE events for each generated workflow field."""
    for field, artifact_type in WORKFLOW_ARTIFACT_UPDATE_FIELD_MAP.items():
        if field not in updates:
            continue
        await publish_workflow_artifact(
            project_id,
            phase,
            artifact_type,
            updates[field],
        )


async def publish_workflow_error(
    project_id: str,
    phase: str,
    message: str,
    *,
    recoverable: bool = False,
) -> None:
    """Broadcast a workflow error event."""
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        get_workflow_sse_hub,
    )

    await get_workflow_sse_hub().publish(
        project_id,
        build_error_event(project_id, phase, message, recoverable=recoverable),
    )


async def publish_workflow_sse_updates(
    project_id: str,
    state: CarouselWorkflowState,
) -> None:
    """Publish phase, review, or error events after workflow transitions."""
    phase = str(state.get("current_phase", ""))
    phase_status = str(state.get("phase_status", ""))
    if not phase:
        return
    await publish_workflow_phase_change(project_id, phase, phase_status)
    if phase_status == PHASE_STATUS_AWAITING_HUMAN:
        await publish_workflow_review_required(project_id, state)
    elif phase_status == PHASE_STATUS_FAILED:
        message = resolve_workflow_sse_error_message(state)
        await publish_workflow_error(project_id, phase, message, recoverable=False)


__all__ = [
    "publish_workflow_artifact",
    "publish_workflow_artifacts_from_updates",
    "publish_workflow_error",
    "publish_workflow_phase_change",
    "publish_workflow_progress",
    "publish_workflow_review_required",
    "publish_workflow_sse_updates",
]
