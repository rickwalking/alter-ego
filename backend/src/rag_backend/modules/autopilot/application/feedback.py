"""Revise feedback loaded from the prompt registry.

The sentence lives in ``agents/prompts/autopilot/v1/revise_feedback.yaml``.
This module only fills the phase, reason, and measured detail.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.modules.autopilot.constants import (
    PROMPT_DOMAIN_AUTOPILOT,
    PROMPT_REVISE_FEEDBACK,
    PROMPT_VERSION_V1,
    VAR_DETAIL,
    VAR_PHASE,
    VAR_REASON,
)


@dataclass(frozen=True, kw_only=True)
class ReviseFeedbackRequest:
    """Values substituted into the revise-feedback template."""

    phase: str
    reason: str
    detail: str


def revise_feedback(request: ReviseFeedbackRequest) -> str:
    """Render the v1 revise-feedback prompt for one failed check."""
    text, _model = render_prompt(
        PROMPT_DOMAIN_AUTOPILOT,
        PROMPT_REVISE_FEEDBACK,
        {
            VAR_PHASE: request.phase,
            VAR_REASON: request.reason,
            VAR_DETAIL: request.detail,
        },
        version=PROMPT_VERSION_V1,
    )
    return text.strip()
