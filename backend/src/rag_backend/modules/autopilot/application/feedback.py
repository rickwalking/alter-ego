"""Revise feedback loaded from the prompt registry.

The sentence lives in ``agents/prompts/autopilot/v2/revise_feedback.yaml``.
This module fills the phase, reason, measured detail and, for a
content-quality failure, one line per failing slide (AE-0392).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.modules.autopilot.constants import (
    PROMPT_DOMAIN_AUTOPILOT,
    PROMPT_REVISE_FEEDBACK,
    REASON_DESIGN,
    REASON_FORBIDDEN,
    REASON_IMAGES,
    REASON_OUTLINE,
    REASON_PERSONA_SCORE,
    REASON_RESEARCH,
    VAR_DETAIL,
    VAR_PHASE,
    VAR_REASON,
)
from rag_backend.modules.autopilot.domain.gate import GateSnapshot
from rag_backend.modules.autopilot.domain.policy import source_has_content
from rag_backend.modules.autopilot.domain.quality import (
    measured_pairs,
    violation_lines,
)
from rag_backend.modules.autopilot.quality_constants import (
    MEASURED_RATIO,
    MEASURED_SEPARATOR,
    PROMPT_VERSION_V2,
    REASON_CONTENT_QUALITY,
    VAR_VIOLATIONS,
)


@dataclass(frozen=True, kw_only=True)
class ReviseFeedbackRequest:
    """Values substituted into the revise-feedback template."""

    phase: str
    reason: str
    detail: str
    violations: tuple[str, ...] = ()


def revise_feedback(request: ReviseFeedbackRequest) -> str:
    """Render the v2 revise-feedback prompt for one failed check."""
    text, _model = render_prompt(
        PROMPT_DOMAIN_AUTOPILOT,
        PROMPT_REVISE_FEEDBACK,
        {
            VAR_PHASE: request.phase,
            VAR_REASON: request.reason,
            VAR_DETAIL: request.detail,
            VAR_VIOLATIONS: list(request.violations),
        },
        version=PROMPT_VERSION_V2,
    )
    return text.strip()


def gate_feedback(snapshot: GateSnapshot, reason: str) -> str:
    """The feedback for one failed gate: what failed and what was measured."""
    violations: tuple[str, ...] = ()
    if reason == REASON_CONTENT_QUALITY:
        violations = violation_lines(snapshot.quality_violations)
    return revise_feedback(
        ReviseFeedbackRequest(
            phase=snapshot.phase,
            reason=reason,
            detail=measured_detail(snapshot, reason),
            violations=violations,
        )
    )


def measured_detail(snapshot: GateSnapshot, reason: str) -> str:
    """What the failed check measured. Never empty (AE-0392)."""
    measure = _MEASURES.get(reason)
    detail = measure(snapshot) if measure is not None else ""
    return detail or snapshot.engine_blocker or reason


def _persona(snapshot: GateSnapshot) -> str:
    if snapshot.persona_score is None:
        return ""
    return str(snapshot.persona_score)


def _research(snapshot: GateSnapshot) -> str:
    return str(sum(1 for source in snapshot.sources if source_has_content(source)))


def _outline(snapshot: GateSnapshot) -> str:
    return MEASURED_RATIO.format(
        got=snapshot.outline_count, expected=snapshot.slides_total
    )


def _images(snapshot: GateSnapshot) -> str:
    return MEASURED_RATIO.format(
        got=len(snapshot.images), expected=snapshot.hero_images_total
    )


def _forbidden(snapshot: GateSnapshot) -> str:
    return MEASURED_SEPARATOR.join(snapshot.forbidden_hits)


def _quality(snapshot: GateSnapshot) -> str:
    return measured_pairs(snapshot.quality_violations)


def _design(snapshot: GateSnapshot) -> str:
    return MEASURED_SEPARATOR.join(snapshot.presentation_blockers)


_MEASURES: dict[str, Callable[[GateSnapshot], str]] = {
    REASON_PERSONA_SCORE: _persona,
    REASON_RESEARCH: _research,
    REASON_OUTLINE: _outline,
    REASON_IMAGES: _images,
    REASON_FORBIDDEN: _forbidden,
    REASON_CONTENT_QUALITY: _quality,
    REASON_DESIGN: _design,
}
