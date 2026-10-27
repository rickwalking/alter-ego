"""Pure rules for editorial resume control flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_AWAITING_HUMAN,
    REVIEW_ACTION_APPROVE,
)

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.editorial_workflow_resume_runner import (
        BackgroundResumeParams,
    )


def _detect_resume_stuck(
    params: BackgroundResumeParams,
    prior_phase: str,
    state: dict[str, object],
) -> bool:
    """Return True when an approve resume completed but phase did not advance."""
    if params.action != REVIEW_ACTION_APPROVE:
        return False
    current_phase = str(state.get("current_phase", ""))
    current_status = str(state.get("phase_status", ""))
    return bool(
        prior_phase
        and current_phase == prior_phase
        and current_status == PHASE_STATUS_AWAITING_HUMAN
    )


__all__ = ["_detect_resume_stuck"]
