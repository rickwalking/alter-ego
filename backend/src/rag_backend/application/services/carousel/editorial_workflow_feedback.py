"""Checkpoint reading and feedback persistence for editorial workflow."""

from __future__ import annotations

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.application.services.carousel.editorial_workflow_types import (
    PhaseFeedbackPersistParams,
)
from rag_backend.domain.constants.carousel_workflow import (
    FINAL_REVIEW_SEND_BACK_PHASES,
)


def _resolve_feedback_phase(params: PhaseFeedbackPersistParams) -> str:
    """Return the phase the note belongs to.

    On a final-review send-back the reviewer targets an earlier phase
    (e.g. ``content``); the note must be filed there so that phase's
    regeneration notes pick it up — not under the current ``final_review``
    phase (AE-0288).
    """
    target = params.target_phase
    if target in FINAL_REVIEW_SEND_BACK_PHASES:
        return str(target)
    return str(params.prior.get("current_phase", ""))


async def read_checkpoint_phase(
    engine: CarouselWorkflowEngine,
    project_id: str,
) -> str:
    """Return current_phase from checkpoint values (ignores pending_next override)."""
    config = engine._run_config(project_id)
    snapshot = await engine._app.aget_state(config)
    if snapshot is None or not isinstance(snapshot.values, dict):
        return ""
    return str(snapshot.values.get("current_phase", ""))


async def persist_phase_feedback(
    engine: CarouselWorkflowEngine,
    params: PhaseFeedbackPersistParams,
) -> None:
    """Store reviewer feedback and increment revision count for the current phase."""
    trimmed = (params.feedback or "").strip()
    if not trimmed:
        return
    phase = _resolve_feedback_phase(params)
    if not phase:
        return
    phase_feedback = dict(params.prior.get("phase_feedback") or {})
    existing = phase_feedback.get(phase, [])
    prior_feedback = existing if isinstance(existing, list) else []
    phase_feedback[phase] = [*prior_feedback, trimmed]
    revision_count = dict(params.prior.get("revision_count") or {})
    count = int(revision_count.get(phase, 0)) + 1
    revision_count[phase] = count
    await engine.update_state(
        params.project_id,
        {
            "phase_feedback": phase_feedback,
            "revision_count": revision_count,
        },
    )


__all__ = [
    "persist_phase_feedback",
    "read_checkpoint_phase",
]
