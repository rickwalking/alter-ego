"""Run lifecycle SSE events on the existing workflow stream (AE-0315).

``run.started`` / ``run.stage_changed`` / ``run.finished`` ride the same
per-project SSE hub the phase events use, so the create-flow client updates
live without polling. Payloads carry no internals — only the project id,
phase, ISO ``run_started_at``, the coarse stage, and a finish reason.
"""

from __future__ import annotations

from datetime import datetime

from rag_backend.application.services.carousel.carousel_run_stage import (
    clear_run_stage,
    set_run_stage,
)
from rag_backend.application.services.carousel.editorial_workflow_sse_build import (
    build_workflow_event,
)
from rag_backend.domain.constants.carousel_run import (
    SSE_EVENT_RUN_FINISHED,
    SSE_EVENT_RUN_STAGE_CHANGED,
    SSE_EVENT_RUN_STARTED,
    SSE_PAYLOAD_FIELD_RUN_REASON,
    SSE_PAYLOAD_FIELD_RUN_STAGE,
    SSE_PAYLOAD_FIELD_RUN_STARTED_AT,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS


def _iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


async def publish_run_started(
    project_id: str,
    phase: str,
    run_started_at: datetime | None,
) -> None:
    """Broadcast run.started when a revision run flips to in_progress."""
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        get_workflow_sse_hub,
    )

    await get_workflow_sse_hub().publish(
        project_id,
        build_workflow_event(
            SSE_EVENT_RUN_STARTED,
            project_id=project_id,
            phase=phase,
            phase_status=PHASE_STATUS_IN_PROGRESS,
            **{SSE_PAYLOAD_FIELD_RUN_STARTED_AT: _iso_or_none(run_started_at)},
        ),
    )


async def publish_run_stage_changed(project_id: str, stage: str) -> None:
    """Broadcast a coarse stage boundary and mirror it for state reads."""
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        get_workflow_sse_hub,
    )

    set_run_stage(project_id, stage)
    await get_workflow_sse_hub().publish(
        project_id,
        build_workflow_event(
            SSE_EVENT_RUN_STAGE_CHANGED,
            project_id=project_id,
            phase_status=PHASE_STATUS_IN_PROGRESS,
            **{SSE_PAYLOAD_FIELD_RUN_STAGE: stage},
        ),
    )


async def publish_run_finished(
    project_id: str,
    reason: str,
    final_phase_status: str | None = None,
) -> None:
    """Broadcast run.finished (completed/failed/stale) and drop the stage."""
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        get_workflow_sse_hub,
    )

    clear_run_stage(project_id)
    payload: dict[str, object] = {
        "project_id": project_id,
        SSE_PAYLOAD_FIELD_RUN_REASON: reason,
    }
    if final_phase_status is not None:
        payload["phase_status"] = final_phase_status
    await get_workflow_sse_hub().publish(
        project_id,
        build_workflow_event(SSE_EVENT_RUN_FINISHED, **payload),
    )


__all__ = [
    "publish_run_finished",
    "publish_run_stage_changed",
    "publish_run_started",
]
