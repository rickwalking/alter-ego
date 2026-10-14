"""Deterministic gate policy (AE-0354).

Gherkin: tests/features/autopilot_runner.feature
"""

from __future__ import annotations

from dataclasses import replace

from rag_backend.domain.constants.carousel import CAROUSEL_HEIGHT, CAROUSEL_WIDTH
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
    PHASE_STATUS_AWAITING,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
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
    ResearchSourceFact,
)
from rag_backend.modules.autopilot.domain.policy import decide, source_has_content

_BELOW = VOICE_MATCH_MIN_SCORE - 0.1


def _source(
    content: str = "body", summary: str = "", points: tuple[str, ...] = ()
) -> ResearchSourceFact:
    return ResearchSourceFact(content=content, summary=summary, key_points=points)


def _jpeg() -> ImageFact:
    return ImageFact(
        present=True,
        is_jpeg=True,
        width=CAROUSEL_WIDTH,
        height=CAROUSEL_HEIGHT,
    )


def _snapshot(**overrides: object) -> GateSnapshot:
    base = GateSnapshot(
        phase=GATE_RESEARCH,
        phase_status=PHASE_STATUS_AWAITING,
        lock_version=1,
        sources=(_source(), _source("b"), _source("c")),
        outline_count=6,
        slides_total=6,
        persona_score=VOICE_MATCH_MIN_SCORE,
        forbidden_hits=(),
        presentation_blockers=(),
        images=tuple(_jpeg() for _ in range(6)),
        revisions_used=0,
        stale=False,
        hero_images_total=6,
    )
    return replace(base, **overrides)


def test_research_passes_at_three_sources_with_content() -> None:
    decision = decide(_snapshot())
    assert decision.action is GateAction.APPROVE
    assert decision.reason == REASON_PASSED


def test_research_accepts_summary_or_key_points() -> None:
    sources = (
        _source(content="", summary="sum", points=()),
        _source(content="", summary="", points=("point",)),
        _source(content="  ", summary="", points=("  ",)),
    )
    assert source_has_content(sources[0]) is True
    assert source_has_content(sources[1]) is True
    assert source_has_content(sources[2]) is False
    decision = decide(_snapshot(sources=sources))
    assert decision.action is GateAction.REVISE
    assert decision.reason == REASON_RESEARCH


def test_research_two_sources_revises() -> None:
    decision = decide(_snapshot(sources=(_source(), _source("b"))))
    assert decision.action is GateAction.REVISE
    assert decision.reason == REASON_RESEARCH


def test_outline_requires_slide_count_match_within_instagram_max() -> None:
    assert decide(_snapshot(phase=GATE_OUTLINE)).action is GateAction.APPROVE
    mismatch = decide(_snapshot(phase=GATE_OUTLINE, outline_count=5))
    assert mismatch.reason == REASON_OUTLINE
    too_many = decide(
        _snapshot(phase=GATE_OUTLINE, slides_total=MAX_SLIDES + 1, outline_count=11)
    )
    assert too_many.reason == REASON_OUTLINE
    empty = decide(_snapshot(phase=GATE_OUTLINE, slides_total=0, outline_count=0))
    assert empty.reason == REASON_OUTLINE


def test_content_floor_is_the_persona_constant() -> None:
    """Scenario: Low persona score is revised then escalated."""
    at_floor = decide(
        _snapshot(phase=GATE_CONTENT, persona_score=VOICE_MATCH_MIN_SCORE)
    )
    assert at_floor.action is GateAction.APPROVE
    below = decide(_snapshot(phase=GATE_CONTENT, persona_score=_BELOW))
    assert below.action is GateAction.REVISE
    assert below.reason == REASON_PERSONA_SCORE
    missing = decide(_snapshot(phase=GATE_CONTENT, persona_score=None))
    assert missing.reason == REASON_PERSONA_SCORE


def test_content_forbidden_phrase_blocks_a_passing_score() -> None:
    decision = decide(
        _snapshot(phase=GATE_CONTENT, persona_score=90.0, forbidden_hits=("synergy",))
    )
    assert decision.action is GateAction.REVISE
    assert decision.reason == REASON_FORBIDDEN


def test_second_failure_revises_and_the_third_escalates() -> None:
    once = decide(
        _snapshot(
            phase=GATE_CONTENT,
            persona_score=_BELOW,
            revisions_used=MAX_REVISES_PER_PHASE - 1,
        )
    )
    assert once.action is GateAction.REVISE
    capped = decide(
        _snapshot(
            phase=GATE_CONTENT,
            persona_score=_BELOW,
            revisions_used=MAX_REVISES_PER_PHASE,
        )
    )
    assert capped.action is GateAction.ESCALATE
    assert capped.reason == REASON_PERSONA_SCORE


def test_design_fails_closed_on_blockers() -> None:
    clean = decide(_snapshot(phase=GATE_DESIGN))
    assert clean.action is GateAction.APPROVE
    blocked = decide(_snapshot(phase=GATE_DESIGN, presentation_blockers=("contrast",)))
    assert blocked.reason == REASON_DESIGN


def test_images_require_every_slide_as_a_sized_jpeg() -> None:
    assert decide(_snapshot(phase=GATE_IMAGES)).action is GateAction.APPROVE
    short = decide(
        _snapshot(phase=GATE_IMAGES, images=tuple(_jpeg() for _ in range(5)))
    )
    assert short.reason == REASON_IMAGES
    for unsized in (replace(_jpeg(), width=0), replace(_jpeg(), height=0)):
        images = tuple(unsized for _ in range(6))
        sized = decide(_snapshot(phase=GATE_IMAGES, images=images))
        assert sized.reason == REASON_IMAGES
    not_jpeg = replace(_jpeg(), is_jpeg=False)
    png = decide(_snapshot(phase=GATE_IMAGES, images=(not_jpeg,) * 6))
    assert png.reason == REASON_IMAGES
    missing = replace(_jpeg(), present=False, is_jpeg=False)
    absent = decide(_snapshot(phase=GATE_IMAGES, images=(missing,) * 6))
    assert absent.reason == REASON_IMAGES


def test_final_review_stops_and_is_never_approved() -> None:
    """Scenario: Clean run reaches the owner."""
    decision = decide(_snapshot(phase=GATE_FINAL_REVIEW, persona_score=_BELOW))
    assert decision.action is GateAction.STOP
    assert decision.reason == REASON_READY


def test_stale_or_failed_phase_escalates_before_the_check() -> None:
    stale = decide(_snapshot(stale=True))
    assert stale.action is GateAction.ESCALATE
    assert stale.reason == REASON_RUN_STALE
    failed = decide(_snapshot(phase_status=PHASE_STATUS_FAILED))
    assert failed.reason == REASON_PHASE_FAILED


def test_in_progress_waits_and_unknown_phase_escalates() -> None:
    waiting = decide(_snapshot(phase_status=PHASE_STATUS_IN_PROGRESS))
    assert waiting.action is GateAction.WAIT
    assert waiting.reason == REASON_WAITING
    unknown = decide(_snapshot(phase="export"))
    assert unknown.action is GateAction.ESCALATE
    assert unknown.reason == REASON_UNEXPECTED_PHASE
