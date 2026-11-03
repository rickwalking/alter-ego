"""The graph-state updates of a reopened final review.

Pedro's decision (2026-11-02): when slide 1 of an approved carousel changes,
its approval is dropped and the owner reviews the new render. The graph parks
an approved carousel at the ``approved_hold`` interrupt; resuming that
interrupt with ``reopen_review`` writes these updates (no approval, a draft,
waiting for a human) and sends the graph back to the ``final_review`` node,
which interrupts again. A later approve there restores
``approved_for_publish`` as any final-review approve does.
"""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.domain.constants.carousel_workflow import (
    CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
    PHASE_FINAL_REVIEW,
    PHASE_STATUS_AWAITING_HUMAN,
    SEND_BACK_TARGET_PHASE_KEY,
)


def reopen_review_updates() -> dict[str, object]:
    """The approval dropped; the hold routes back to the final review."""
    return {
        "current_phase": PHASE_FINAL_REVIEW,
        "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        "workflow_status": CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
        "quality_passed": False,
        SEND_BACK_TARGET_PHASE_KEY: PHASE_FINAL_REVIEW,
    }


def reopens_final_review(state: Mapping[str, object]) -> bool:
    """True when a resumed hold asks for the final review again."""
    return (
        state.get("phase_status") == PHASE_STATUS_AWAITING_HUMAN
        and state.get(SEND_BACK_TARGET_PHASE_KEY) == PHASE_FINAL_REVIEW
    )


__all__ = ["reopen_review_updates", "reopens_final_review"]
