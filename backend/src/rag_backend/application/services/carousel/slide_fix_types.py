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
from rag_backend.domain.constants.slide_fix import AUTOFIX_MODEL_ATTEMPTS


class SlideRewriter(Protocol):
    """One model call: the slide-fix prompt in, the raw answer out."""

    async def rewrite(self, prompt: str) -> str:
        """Raises on a transport or provider failure."""
        ...


class VoiceScorer(Protocol):
    """The persona's voice-match score (0-100) of one slide's PT copy."""

    async def score(self, text: str) -> float:
        """Raises on a transport or provider failure."""
        ...


@dataclass(frozen=True)
class SlideFixSettings:
    """How hard to try: attempts per slide, parallel slides, the voice floor."""

    attempts: int = AUTOFIX_MODEL_ATTEMPTS
    concurrency: int = 1
    voice_floor: float = VOICE_MATCH_MIN_SCORE


@dataclass(frozen=True)
class SlideFixTools:
    """The model, the optional voice scorer and the persona style guide."""

    rewriter: SlideRewriter
    scorer: VoiceScorer | None = None
    style_guide: str = ""


@dataclass(frozen=True)
class SlideIssue:
    """One failing check of one slide: a blocking rule or the voice floor."""

    code: str
    message: str
    locale: str = ""
    field: str = ""


@dataclass(frozen=True)
class SlideTarget:
    """A slide to fix: its record, what fails, its voice score and role."""

    slide_index: int
    record: dict[str, object]
    issues: tuple[SlideIssue, ...]
    score: float | None = None
    role: str = ""


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


@dataclass(frozen=True)
class SlideFixResult:
    """Where one slide ended: fixed or not, its copy, score and attempts."""

    slide_index: int
    fixed: bool
    record: dict[str, object]
    issues: tuple[SlideIssue, ...]
    attempts: tuple[FixAttempt, ...]
    score: float | None = None


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
