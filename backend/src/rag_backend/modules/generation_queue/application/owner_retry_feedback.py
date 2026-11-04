"""The fixed, system-written feedback line of an owner Retry revise.

The sentence lives in ``agents/prompts/owner_retry/v1/retry_feedback.yaml``.
This module fills the phase, the reason and, when the checkpoint carries a
persona score below the voice floor, the score and the threshold. The line is
sent as the revise feedback and stored in the ``carousel.retry.requested``
audit, so a retry revision is told apart from an owner one.
"""

from __future__ import annotations

from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.domain.constants.persona import VOICE_MATCH_MIN_SCORE
from rag_backend.modules.generation_queue.constants import (
    RETRY_DETAIL_SCORE,
    RETRY_PROMPT_DOMAIN,
    RETRY_PROMPT_FEEDBACK,
    RETRY_PROMPT_VERSION,
    RETRY_VAR_DETAIL,
    RETRY_VAR_PHASE,
    RETRY_VAR_REASON,
)
from rag_backend.modules.generation_queue.domain.owner_retry import RetryFacts


def retry_feedback(facts: RetryFacts, reason: str) -> str:
    """The feedback line for a revise of the carousel's current phase."""
    text, _model = render_prompt(
        RETRY_PROMPT_DOMAIN,
        RETRY_PROMPT_FEEDBACK,
        {
            RETRY_VAR_PHASE: facts.carousel.phase,
            RETRY_VAR_REASON: reason,
            RETRY_VAR_DETAIL: _score_detail(facts.checkpoint.persona_score),
        },
        version=RETRY_PROMPT_VERSION,
    )
    return text.strip()


def _score_detail(score: float | None) -> str:
    """The persona score and the floor, only when the score is below it."""
    if score is None or score >= VOICE_MATCH_MIN_SCORE:
        return ""
    return RETRY_DETAIL_SCORE.format(score=score, threshold=VOICE_MATCH_MIN_SCORE)


__all__ = ["retry_feedback"]
