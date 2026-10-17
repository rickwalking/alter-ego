"""A content gate with no persona scores is approved like the engine (AE-0364).

Feature: autopilot_runner.feature (AE-0364 scenarios)

Prod 2026-10-14, carousel 8e350d6e: the autopilot attaches no persona, so the
content phase produced 7 drafts and ``persona_scores = {}``. The engine skips
the voice floor when there are no scores; the policy treated "no score" as a
failure and revised the content gate until it escalated.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import pytest

from rag_backend.application.services.carousel.editorial_workflow_service_helpers import (
    validate_content_approve_persona_score,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_PRESENTATION_VALIDATION_BLOCKED,
)
from rag_backend.modules.autopilot.constants import (
    FIELD_CURRENT_PHASE,
    FIELD_FORBIDDEN_PHRASES,
    FIELD_OVERALL,
    FIELD_PERSONA_SCORES,
    FIELD_PHASE_STATUS,
    FIELD_SLIDE_DRAFTS,
    GATE_CONTENT,
    PHASE_STATUS_AWAITING,
    REASON_DESIGN,
    REASON_FORBIDDEN,
    REASON_PASSED,
    REASON_PERSONA_SCORE,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateAction,
    PolicyDecision,
    SnapshotParts,
)
from rag_backend.modules.autopilot.domain.messages import ScoreSummary, album_caption
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.domain.snapshot import assemble_snapshot

_SLIDES = 7
_DRAFTS = [{"draft_text": f"Draft {i}"} for i in range(_SLIDES)]
_LOW = 62
_HIGH = 75


def _state(**extra: object) -> dict[str, object]:
    return {
        FIELD_CURRENT_PHASE: GATE_CONTENT,
        FIELD_PHASE_STATUS: PHASE_STATUS_AWAITING,
        FIELD_SLIDE_DRAFTS: list(_DRAFTS),
        **extra,
    }


def _engine_refusal(state: Mapping[str, object]) -> str | None:
    """The engine's own persona check: its error code, or None when it passes."""
    try:
        validate_content_approve_persona_score(cast(CarouselWorkflowState, dict(state)))
    except ValueError as exc:
        return str(exc)
    return None


def _decide(state: Mapping[str, object], blocker: str = "") -> PolicyDecision:
    snapshot = assemble_snapshot(
        SnapshotParts(
            state=state,
            images=(),
            slides_total=_SLIDES,
            lock_version=1,
            stale=False,
            engine_blocker=blocker,
        )
    )
    return decide(snapshot)


@pytest.mark.parametrize("scores", [{}, None, [], "unscored"])
def test_no_persona_scores_approves_like_the_engine(scores: object) -> None:
    """Scenario: A content gate with no persona scores is approved like the engine."""
    state = _state(**{FIELD_PERSONA_SCORES: scores})

    decision = _decide(state)

    assert decision.action is GateAction.APPROVE
    assert decision.reason == REASON_PASSED
    assert _engine_refusal(state) is None


def test_missing_persona_scores_key_approves() -> None:
    """Scenario: A content gate with no persona scores is approved like the engine."""
    assert _decide(_state()).action is GateAction.APPROVE


def test_score_of_62_revises_and_the_engine_agrees() -> None:
    """Scenario: Persona scores, when present, still enforce the voice floor."""
    state = _state(**{
        FIELD_PERSONA_SCORES: {
            "slide_1": {FIELD_OVERALL: 80},
            "slide_2": {FIELD_OVERALL: _LOW},
        }
    })

    decision = _decide(state)

    assert decision.action is GateAction.REVISE
    assert decision.reason == REASON_PERSONA_SCORE
    assert _engine_refusal(state) == ERR_PERSONA_SCORE_TOO_LOW


def test_score_of_75_approves_and_the_engine_agrees() -> None:
    """Scenario: Persona scores, when present, still enforce the voice floor."""
    state = _state(**{FIELD_PERSONA_SCORES: {"slide_1": {FIELD_OVERALL: _HIGH}}})

    decision = _decide(state)

    assert decision.action is GateAction.APPROVE
    assert _engine_refusal(state) is None


def test_unscored_run_still_fails_on_a_forbidden_phrase() -> None:
    """Scenario: An unscored run still fails on forbidden phrases and engine blockers."""
    state = _state(**{FIELD_PERSONA_SCORES: {}, FIELD_FORBIDDEN_PHRASES: ["Draft 3"]})

    decision = _decide(state)

    assert decision.action is GateAction.REVISE
    assert decision.reason == REASON_FORBIDDEN


def test_unscored_run_still_fails_on_an_engine_blocker() -> None:
    """Scenario: An unscored run still fails on forbidden phrases and engine blockers."""
    decision = _decide(
        _state(**{FIELD_PERSONA_SCORES: {}}),
        ERR_PRESENTATION_VALIDATION_BLOCKED,
    )

    assert decision.action is GateAction.REVISE
    assert decision.reason == REASON_DESIGN


@pytest.mark.parametrize(
    "entry",
    [{FIELD_OVERALL: None}, {FIELD_OVERALL: "high"}, "high", True],
)
def test_unreadable_persona_score_is_unscored(entry: object) -> None:
    """Scenario: An unreadable persona score is unscored (AE-0407)."""
    state = _state(**{FIELD_PERSONA_SCORES: {"slide_1": entry}})

    snapshot = assemble_snapshot(
        SnapshotParts(
            state=state,
            images=(),
            slides_total=_SLIDES,
            lock_version=1,
            stale=False,
        )
    )

    assert snapshot.persona_score is None
    assert decide(snapshot).reason != REASON_PERSONA_SCORE


def test_review_caption_says_not_scored() -> None:
    """Scenario: The owner sees that the run was not scored."""
    unscored = album_caption(
        ScoreSummary(title="Agents", persona_score=None, sources_count=4)
    )
    scored = album_caption(
        ScoreSummary(title="Agents", persona_score=_HIGH, sources_count=4)
    )

    assert unscored == "Agents\nPersona: not scored · 4 sources"
    assert scored == "Agents\nPersona: 75 · 4 sources"
