"""Reviewer-note history for the workflow state response (AE-0413).

AE-0405 moves a content note out of ``phase_feedback`` once the regeneration
used it, so ``phase_feedback.content`` reads ``[]`` after every content
revision even though the note was applied. The consumed notes live in
``phase_feedback_history``; this extractor exposes them on the API.
"""

from __future__ import annotations

from rag_backend.api.schemas.carousel_workflow import (
    PhaseFeedbackHistoryEntryResponse,
)
from rag_backend.application.services.carousel.content_feedback_lifecycle import (
    feedback_history,
)
from rag_backend.domain.constants.content_feedback import (
    STATE_FIELD_FEEDBACK_HISTORY,
)


def phase_feedback_history_field(
    state: dict[str, object],
) -> dict[str, list[PhaseFeedbackHistoryEntryResponse]]:
    """Consumed notes per phase, oldest first (phases without notes omitted)."""
    raw = state.get(STATE_FIELD_FEEDBACK_HISTORY)
    if not isinstance(raw, dict):
        return {}
    history: dict[str, list[PhaseFeedbackHistoryEntryResponse]] = {}
    for phase in raw:
        entries = [
            PhaseFeedbackHistoryEntryResponse(**entry)
            for entry in feedback_history(state, str(phase))
        ]
        if entries:
            history[str(phase)] = entries
    return history


__all__ = ["phase_feedback_history_field"]
