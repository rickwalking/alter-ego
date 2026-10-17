"""Checkpoint reading and feedback persistence for editorial workflow."""

from __future__ import annotations

from typing import cast

from rag_backend.agents.carousel_workflow import (
    CarouselWorkflowEngine,
    checkpoint_gate_phase,
)
from rag_backend.application.services.carousel.content_feedback_lifecycle import (
    NewFeedbackNote,
    add_feedback_note,
    settle_stale_content_feedback,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    PhaseFeedbackPersistParams,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
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
    """Return the phase of the gate the checkpoint is parked at.

    AE-0413: this used to return the raw stored ``current_phase``, which on the
    first content gate still said ``outline`` (the content node is interrupted,
    so its return value was never committed) while the API state said
    ``content``. The structured-feedback guard then 422'd the manual fixes
    (``edited_localized_slides_phase_not_allowed``). The pending node decides.
    """
    config = engine._run_config(project_id)
    snapshot = await engine._app.aget_state(config)
    if snapshot is None:
        return ""
    return checkpoint_gate_phase(snapshot)


async def persist_phase_feedback(
    engine: CarouselWorkflowEngine,
    params: PhaseFeedbackPersistParams,
) -> None:
    """Store reviewer feedback and increment the charged phase's revision count.

    The counter is keyed by the phase that will re-run (target phase on a
    send-back, current phase otherwise). ``count_revision=False`` (AE-0310)
    stores the note only — uncapped submissions never consume the budget.
    """
    trimmed = (params.feedback or "").strip()
    if not trimmed:
        return
    phase = _resolve_feedback_phase(params)
    if not phase:
        return
    # AE-0405: the note is tagged (source + time) so the regeneration that
    # uses it can move it to the history.
    updates = add_feedback_note(
        params.prior,
        NewFeedbackNote(phase=phase, note=trimmed, source=params.source),
    )
    if params.count_revision:
        revision_count = dict(params.prior.get("revision_count") or {})
        revision_count[phase] = int(revision_count.get(phase, 0)) + 1
        updates["revision_count"] = revision_count
    await engine.update_state(params.project_id, updates)


async def settle_feedback_before_resume(
    engine: CarouselWorkflowEngine,
    prior: CarouselWorkflowState,
    action: str,
) -> CarouselWorkflowState:
    """Settle content notes no regeneration will use; return the updated prior.

    AE-0405 migration on read: legacy untagged notes already steered the last
    regeneration and move to the history; an active autopilot note is dropped
    once the content gate is approved.
    """
    updates = settle_stale_content_feedback(prior, action)
    if not updates:
        return prior
    await engine.update_state(str(prior.get("project_id", "")), updates)
    return cast(CarouselWorkflowState, {**prior, **updates})


__all__ = [
    "persist_phase_feedback",
    "read_checkpoint_phase",
    "settle_feedback_before_resume",
]
