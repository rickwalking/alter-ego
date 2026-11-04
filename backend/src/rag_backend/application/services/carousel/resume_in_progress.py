"""The workflow state a resume flips the carousel row to before its run starts."""

from __future__ import annotations

from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
    PHASE_STATUS_IN_PROGRESS,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)


def in_progress_state(
    prior: CarouselWorkflowState | None, project_id: str
) -> CarouselWorkflowState:
    """``prior`` at ``in_progress``; an approved carousel drops back to draft.

    Resuming an already-approved carousel (a final-review send-back) drops the
    publish lock with the flip, so a concurrent publish cannot ship stale content
    while the workflow re-runs.
    """
    current_phase = str(prior.get("current_phase", "")) if prior else ""
    state: CarouselWorkflowState = {
        **(prior or {}),
        "project_id": project_id,
        "current_phase": current_phase,
        "phase_status": PHASE_STATUS_IN_PROGRESS,
    }
    if str((prior or {}).get("workflow_status", "")) == (
        WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
    ):
        state["workflow_status"] = CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT
    return state


__all__ = ["in_progress_state"]
