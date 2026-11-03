"""Map a human review response onto carousel graph-state updates.

Split from ``carousel_workflow_nodes`` (which re-exports it) so the node module
does not grow. A reviewer's slide edits are applied at every phase that allows
them; ``reopen_review`` (an approved carousel whose slide 1 changed) drops the
approval and sends the approved hold back to the final review.
"""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.agents.carousel_review_reopen import reopen_review_updates
from rag_backend.domain.constants.carousel_workflow import (
    CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
    CAROUSEL_WORKFLOW_PHASES,
    EDITED_SLIDES_ALLOWED_PHASES,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_AWAITING_HUMAN,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REJECT,
    REVIEW_ACTION_REOPEN,
    REVIEW_ACTION_REVISE,
    SEND_BACK_TARGET_PHASE_KEY,
    STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY,
    STRUCTURED_FEEDBACK_KEY,
    STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
)
from rag_backend.modules.presentation import (
    apply_localized_slide_edits_via_port,
)


def _edited_slide_updates(
    review: dict[str, object],
    state: Mapping[str, object] | None,
    phase: str | None,
) -> dict[str, object]:
    """Apply reviewer slide edits to workflow state updates.

    Uniform semantics at every allowed phase (content, design, final_review):
    apply the edits to ``localized_slides``, re-run presentation validation,
    and store the fresh report.
    """
    if phase not in EDITED_SLIDES_ALLOWED_PHASES or state is None:
        return {}
    structured = review.get(STRUCTURED_FEEDBACK_KEY)
    if not isinstance(structured, dict):
        return {}
    edited = structured.get(STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY)
    if not isinstance(edited, list) or not edited:
        return {}
    edited_dicts = [slide for slide in edited if isinstance(slide, dict)]
    return apply_localized_slide_edits_via_port(state, edited_dicts)


def review_updates_from_response(
    review: dict[str, object],
    *,
    state: Mapping[str, object] | None = None,
    phase: str | None = None,
) -> dict[str, object]:
    """Map a review response onto graph-state updates.

    Any revise or reject drops the publish approval in the graph state; otherwise
    get_state copies a stale approved_for_publish back to the DB on the resume sync and
    reopens a stale-publish window for the whole revision. This also covers a revise
    without a target from a held carousel, since a stale send-back target could still
    route it to an earlier phase. The later final_review re-approval restores
    approved_for_publish.
    """
    action = review.get("action")
    edit_updates = _edited_slide_updates(review, state, phase)
    if action == REVIEW_ACTION_APPROVE:
        return {**edit_updates, "phase_status": PHASE_STATUS_APPROVED}
    if action == REVIEW_ACTION_REOPEN:
        return reopen_review_updates()
    if action not in {REVIEW_ACTION_REVISE, REVIEW_ACTION_REJECT}:
        return {"phase_status": PHASE_STATUS_AWAITING_HUMAN}
    updates: dict[str, object] = {
        **edit_updates,
        "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        "workflow_status": CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
        "quality_passed": False,
    }
    structured = review.get(STRUCTURED_FEEDBACK_KEY)
    if isinstance(structured, dict):
        target = structured.get(STRUCTURED_FEEDBACK_TARGET_PHASE_KEY)
        if isinstance(target, str) and target in CAROUSEL_WORKFLOW_PHASES:
            updates[SEND_BACK_TARGET_PHASE_KEY] = target
            updates["current_phase"] = target
    return updates


__all__ = ["review_updates_from_response"]
