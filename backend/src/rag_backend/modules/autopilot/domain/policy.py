"""Deterministic auto-approve checks (architecture §6).

A failed check revises at most twice (design: once), then escalates. ``final_review``
is never approved. The persona floor is the persona module's constant.
"""

from __future__ import annotations

from collections.abc import Callable

from rag_backend.domain.constants.carousel_workflow import (
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_PRESENTATION_VALIDATION_BLOCKED,
)
from rag_backend.domain.constants.persona import VOICE_MATCH_MIN_SCORE
from rag_backend.modules.autopilot.constants import (
    GATE_CONTENT,
    GATE_DESIGN,
    GATE_FINAL_REVIEW,
    GATE_IMAGES,
    GATE_OUTLINE,
    GATE_RESEARCH,
    MAX_REVISES_PER_PHASE,
    MAX_SLIDES,
    MIN_RESEARCH_SOURCES,
    PHASE_STATUS_AWAITING,
    PHASE_STATUS_FAILED,
    REASON_DESIGN,
    REASON_FORBIDDEN,
    REASON_IMAGES,
    REASON_OUTLINE,
    REASON_PASSED,
    REASON_PERSONA_SCORE,
    REASON_PHASE_FAILED,
    REASON_READY,
    REASON_RESEARCH,
    REASON_RUN_STALE,
    REASON_UNEXPECTED_PHASE,
    REASON_WAITING,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateAction,
    GateSnapshot,
    ImageFact,
    PolicyDecision,
    ResearchSourceFact,
)
from rag_backend.modules.autopilot.parked_constants import (
    REASON_ENGINE_PARKED,
    REDRIVABLE_PHASE_STATUSES,
)
from rag_backend.modules.autopilot.pov_constants import REASON_PERSONA_NOT_SCORED
from rag_backend.modules.autopilot.quality_constants import REASON_CONTENT_QUALITY
from rag_backend.modules.autopilot.recovery_constants import (
    MAX_REVISES_DESIGN,
    REASON_ENGINE_ERROR,
)

Check = Callable[[GateSnapshot], str | None]


def source_has_content(source: ResearchSourceFact) -> bool:
    """True when the finding has body text, a summary, or a key point."""
    if source.content.strip() or source.summary.strip():
        return True
    return any(point.strip() for point in source.key_points)


def decide(snapshot: GateSnapshot) -> PolicyDecision:
    """Choose approve, revise, escalate, stop, or wait."""
    early = _before_gate(snapshot)
    if early is not None:
        return early
    if snapshot.phase_status != PHASE_STATUS_AWAITING:
        return PolicyDecision(action=GateAction.WAIT, reason=REASON_WAITING)
    if snapshot.phase == GATE_FINAL_REVIEW:
        return PolicyDecision(action=GateAction.STOP, reason=REASON_READY)
    check = _CHECKS.get(snapshot.phase)
    if check is None:
        return PolicyDecision(
            action=GateAction.ESCALATE,
            reason=REASON_UNEXPECTED_PHASE,
        )
    return _from_check(snapshot, check(snapshot))


def _before_gate(snapshot: GateSnapshot) -> PolicyDecision | None:
    """A stale or failed run, then a parked workflow (AE-0363), come first."""
    terminal = _terminal(snapshot)
    if terminal is not None:
        return terminal
    if snapshot.parked:
        return _parked(snapshot)
    return None


def _terminal(snapshot: GateSnapshot) -> PolicyDecision | None:
    if snapshot.stale:
        return PolicyDecision(action=GateAction.ESCALATE, reason=REASON_RUN_STALE)
    if snapshot.phase_status == PHASE_STATUS_FAILED:
        return PolicyDecision(action=GateAction.ESCALATE, reason=REASON_PHASE_FAILED)
    return None


def _parked(snapshot: GateSnapshot) -> PolicyDecision:
    """Never wait on a parked workflow past the grace period (AE-0363)."""
    if not snapshot.parked_overdue:
        return PolicyDecision(action=GateAction.WAIT, reason=REASON_WAITING)
    if snapshot.phase_status in REDRIVABLE_PHASE_STATUSES:
        return PolicyDecision(action=GateAction.REDRIVE, reason=REASON_ENGINE_PARKED)
    return PolicyDecision(action=GateAction.ESCALATE, reason=REASON_ENGINE_PARKED)


def _from_check(snapshot: GateSnapshot, reason: str | None) -> PolicyDecision:
    if reason is None:
        return PolicyDecision(action=GateAction.APPROVE, reason=REASON_PASSED)
    if reason in _NO_REVISE_REASONS or snapshot.revisions_used >= _revise_cap(
        snapshot.phase
    ):
        return PolicyDecision(action=GateAction.ESCALATE, reason=reason)
    return PolicyDecision(action=GateAction.REVISE, reason=reason)


def _research(snapshot: GateSnapshot) -> str | None:
    usable = sum(1 for source in snapshot.sources if source_has_content(source))
    if usable >= MIN_RESEARCH_SOURCES:
        return None
    return REASON_RESEARCH


def _outline(snapshot: GateSnapshot) -> str | None:
    if snapshot.slides_total < 1 or snapshot.slides_total > MAX_SLIDES:
        return REASON_OUTLINE
    if snapshot.outline_count != snapshot.slides_total:
        return REASON_OUTLINE
    return None


def _content(snapshot: GateSnapshot) -> str | None:
    """Mirror the engine's content-approve rule (AE-0364).

    The engine enforces the voice floor only when persona scores exist; a
    Radar IA run with no persona has none, so the voice check is skipped.
    PR #106 review: a POV run is never approved unscored; it escalates with
    ``persona_not_scored`` (a revise cannot add the missing persona).
    Forbidden phrases, blocking presentation rules (AE-0392) and the engine's
    refusal still apply.
    """
    score = snapshot.persona_score
    if score is None and snapshot.pov:
        return REASON_PERSONA_NOT_SCORED
    if score is not None and score < VOICE_MATCH_MIN_SCORE:
        return REASON_PERSONA_SCORE
    if snapshot.forbidden_hits:
        return REASON_FORBIDDEN
    if snapshot.quality_violations:
        return REASON_CONTENT_QUALITY
    return _engine_reason(snapshot.engine_blocker)


def _engine_reason(blocker: str) -> str | None:
    """Map the engine's content-approve refusal onto a policy reason."""
    if not blocker:
        return None
    return _ENGINE_REASONS.get(blocker, REASON_ENGINE_ERROR)


def _revise_cap(phase: str) -> int:
    """Design revises once (architecture §6); the other gates twice."""
    if phase == GATE_DESIGN:
        return MAX_REVISES_DESIGN
    return MAX_REVISES_PER_PHASE


def _design(snapshot: GateSnapshot) -> str | None:
    """Blocking presentation rules are content quality (AE-0392).

    A missing or rule-less blocking report stays a design failure.
    """
    if not snapshot.presentation_blockers:
        return None
    if snapshot.quality_violations:
        return REASON_CONTENT_QUALITY
    return REASON_DESIGN


def _images(snapshot: GateSnapshot) -> str | None:
    """One valid hero JPEG per slide the image phase illustrates (AE-0365).

    The CTA slide uses the owner avatar, so a 7-slide run stores 6 hero
    images. The count comes from the pipeline's own slide filter, not from
    ``slides_total``; zero (no slides persisted) fails closed.
    """
    expected = snapshot.hero_images_total
    if expected < 1 or expected > MAX_SLIDES:
        return REASON_IMAGES
    if len(snapshot.images) != expected:
        return REASON_IMAGES
    if any(not _valid_jpeg(image) for image in snapshot.images):
        return REASON_IMAGES
    return None


def _valid_jpeg(image: ImageFact) -> bool:
    """A present JPEG with a decodable size (AE-0362).

    ``image_assets`` are the raw hero images (OpenAI renders 1536x1024), not
    the 1080x1350 slides: those are composed later, at finalize. Requiring the
    slide size here could never pass on a real run.
    """
    return image.present and image.is_jpeg and image.width > 0 and image.height > 0


# Escalate at once: revising cannot fix these.
_NO_REVISE_REASONS = frozenset({REASON_PERSONA_NOT_SCORED})

_ENGINE_REASONS: dict[str, str] = {
    ERR_PERSONA_SCORE_TOO_LOW: REASON_PERSONA_SCORE,
    ERR_PRESENTATION_VALIDATION_BLOCKED: REASON_DESIGN,
}

_CHECKS: dict[str, Check] = {
    GATE_RESEARCH: _research,
    GATE_OUTLINE: _outline,
    GATE_CONTENT: _content,
    GATE_DESIGN: _design,
    GATE_IMAGES: _images,
}
