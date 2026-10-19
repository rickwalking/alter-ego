"""Types of the autopilot model fix of failing slides (AE-0401).

The editorial facade injects the model (``SlideRewriter``) and the persona
voice scorer (``VoiceScorer``), so the application layer imports neither the
agents nor the infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rag_backend.application.services.carousel.owner_autofix_plan import (
    AutofixContext,
)
from rag_backend.domain.constants.persona import VOICE_MATCH_MIN_SCORE
from rag_backend.domain.constants.slide_fix import (
    AUTOFIX_ESCALATION_ATTEMPTS,
    AUTOFIX_MODEL_ATTEMPTS,
    MODEL_ROLE_FAST,
)


class SlideRewriter(Protocol):
    """One model call: the slide-fix prompt in, the raw answer out."""

    async def rewrite(self, prompt: str) -> str:
        """Raises on a transport or provider failure."""
        ...


class VoiceScorer(Protocol):
    """The persona's voice-match score (0-100) of one slide's PT copy."""

    async def score(self, text: str) -> float | None:
        """None when the judge gave no score (AE-0407); may raise."""
        ...


@dataclass(frozen=True)
class SlideFixSettings:
    """How hard to try: attempts per slide, parallel slides, the voice floor.

    ``escalation_attempts`` more attempts run on ``escalation_rewriter``
    (the reasoning model) after ``attempts`` failed ones (AE-0407).
    """

    attempts: int = AUTOFIX_MODEL_ATTEMPTS
    escalation_attempts: int = AUTOFIX_ESCALATION_ATTEMPTS
    concurrency: int = 1
    voice_floor: float = VOICE_MATCH_MIN_SCORE


@dataclass(frozen=True)
class SlideFixTools:
    """The models, the optional voice scorer and the persona style guide."""

    rewriter: SlideRewriter
    scorer: VoiceScorer | None = None
    style_guide: str = ""
    escalation_rewriter: SlideRewriter | None = None


@dataclass(frozen=True)
class SlideIssue:
    """One failing check of one slide: a blocking rule or the voice floor."""

    code: str
    message: str
    locale: str = ""
    field: str = ""


@dataclass(frozen=True)
class SlideTarget:
    """A slide to fix: its record, what fails, its voice score and role.

    AE-0433: ``unscored_ticks`` > 0 means the stored score is stale (the
    judge gave no score for the current copy on that many ticks): the copy
    is re-scored before any rewrite.
    """

    slide_index: int
    record: dict[str, object]
    issues: tuple[SlideIssue, ...]
    score: float | None = None
    role: str = ""
    unscored_ticks: int = 0


@dataclass(frozen=True)
class DeckContext:
    """The whole checkpoint copy a candidate slide is validated against."""

    records: list[dict[str, object]]
    policy_version: str
    autofix: AutofixContext
    scored: bool


@dataclass(frozen=True)
class FixAttempt:
    """One model attempt on one slide, for the per-attempt log."""

    slide_index: int
    attempt: int
    rules_before: tuple[str, ...]
    rules_after: tuple[str, ...]
    outcome: str
    model_role: str = MODEL_ROLE_FAST


@dataclass(frozen=True)
class SlideFixResult:
    """Where one slide ended: fixed or not, its copy, score and attempts.

    AE-0433: a fixed slide whose copy the judge could not score keeps its
    old ``score`` and counts ``unscored_ticks`` (> 0) for a re-score.
    """

    slide_index: int
    fixed: bool
    record: dict[str, object]
    issues: tuple[SlideIssue, ...]
    attempts: tuple[FixAttempt, ...]
    score: float | None = None
    unscored_ticks: int = 0


@dataclass(frozen=True)
class SlideFixCommand:
    """Fix one carousel's failing slides at the lock version the caller read."""

    project_id: str
    expected_version: int
    phase: str


@dataclass(frozen=True)
class SlideFixOutcome:
    """``status`` is ``AUTOFIX_STATUS_*``; ``results`` cover every target."""

    status: str
    results: tuple[SlideFixResult, ...] = ()
    unfixable_rules: tuple[str, ...] = ()


__all__ = [
    "DeckContext",
    "FixAttempt",
    "SlideFixCommand",
    "SlideFixOutcome",
    "SlideFixResult",
    "SlideFixSettings",
    "SlideFixTools",
    "SlideIssue",
    "SlideRewriter",
    "SlideTarget",
    "VoiceScorer",
]
