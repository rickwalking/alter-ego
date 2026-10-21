"""Snapshot assembly from workflow state."""

from __future__ import annotations

from rag_backend.modules.autopilot.constants import (
    BLOCKER_BLOCKING,
    BLOCKER_MISSING,
    FIELD_BLOCKING,
    FIELD_CODE,
    FIELD_CONTENT,
    FIELD_CONTENT_GATE,
    FIELD_CURRENT_PHASE,
    FIELD_FORBIDDEN_PHRASES,
    FIELD_KEY_POINTS,
    FIELD_OUTLINE,
    FIELD_OVERALL,
    FIELD_PERSONA_SCORES,
    FIELD_PHASE_STATUS,
    FIELD_PRESENTATION_VALIDATION,
    FIELD_REVISION_COUNT,
    FIELD_SEVERITY,
    FIELD_SLIDE_DRAFTS,
    FIELD_SUMMARY,
    FIELD_VIOLATIONS,
    GATE_CONTENT,
    GATE_DESIGN,
    PHASE_STATUS_AWAITING,
    SEVERITY_BLOCKER,
)
from rag_backend.modules.autopilot.domain.gate import ImageFact, SnapshotParts
from rag_backend.modules.autopilot.domain.snapshot import assemble_snapshot


def _parts(
    state: dict[str, object],
    images: tuple[ImageFact, ...] = (),
    slides: int = 6,
    lock: int = 1,
    stale: bool = False,
) -> SnapshotParts:
    return SnapshotParts(
        state=state,
        images=images,
        slides_total=slides,
        lock_version=lock,
        stale=stale,
    )


_IMAGE = ImageFact(present=True, is_jpeg=True, width=1, height=1)


def test_persona_score_is_the_minimum_overall() -> None:
    state = {
        FIELD_CURRENT_PHASE: "content",
        FIELD_PHASE_STATUS: PHASE_STATUS_AWAITING,
        FIELD_PERSONA_SCORES: {
            "voice": {FIELD_OVERALL: 80},
            "tone": {FIELD_OVERALL: 62.5},
        },
    }
    snapshot = assemble_snapshot(_parts(state, slides=6, lock=3))
    assert snapshot.persona_score == 62.5
    assert snapshot.lock_version == 3


def test_persona_dict_without_overall_is_unscored_like_the_engine() -> None:
    """Scenario: The engine and the policy read a missing "overall" the same way.

    QA r1 B1: the snapshot must read like the engine, or the policy approves
    into a refusal. Both skip an entry without ``overall`` (a
    failed judge call), so the lowest score is the scored one.
    """
    state = {
        FIELD_CURRENT_PHASE: "content",
        FIELD_PHASE_STATUS: PHASE_STATUS_AWAITING,
        FIELD_PERSONA_SCORES: {"voice": {FIELD_OVERALL: 80}, "empty": {}},
    }
    snapshot = assemble_snapshot(_parts(state, slides=6, lock=3))
    assert snapshot.persona_score == 80.0


def test_missing_persona_scores_stay_none() -> None:
    snapshot = assemble_snapshot(_parts({}))
    assert snapshot.persona_score is None


def test_pending_rescores_are_listed_by_slide() -> None:
    """The gate read sees the stale-score markers."""
    state = {
        FIELD_CURRENT_PHASE: "content",
        FIELD_PHASE_STATUS: PHASE_STATUS_AWAITING,
        FIELD_PERSONA_SCORES: {
            "slide_3": {
                FIELD_OVERALL: 80,
                "rescore_pending": True,
                "unscored_ticks": 2,
            },
            "slide_5": {FIELD_OVERALL: 70},
        },
    }
    snapshot = assemble_snapshot(_parts(state, slides=6, lock=3))
    assert snapshot.pending_rescores == (3,)
    assert snapshot.persona_score == 70.0


def test_no_pending_rescores_without_markers() -> None:
    state = {
        FIELD_CURRENT_PHASE: "content",
        FIELD_PHASE_STATUS: PHASE_STATUS_AWAITING,
        FIELD_PERSONA_SCORES: {"slide_3": {FIELD_OVERALL: 80}},
    }
    snapshot = assemble_snapshot(_parts(state, slides=6, lock=3))
    assert snapshot.pending_rescores == ()


def test_research_findings_keep_content_summary_and_points() -> None:
    state = {
        "research_findings": [
            {FIELD_CONTENT: "body", FIELD_SUMMARY: "", FIELD_KEY_POINTS: ["a"]},
            "skip",
        ]
    }
    snapshot = assemble_snapshot(_parts(state, slides=1))
    assert len(snapshot.sources) == 1
    assert snapshot.sources[0].content == "body"
    assert snapshot.sources[0].key_points == ("a",)


def test_outline_length_and_revision_count_follow_the_phase() -> None:
    state = {
        FIELD_CURRENT_PHASE: "outline",
        FIELD_OUTLINE: [{}, {}],
        FIELD_REVISION_COUNT: {"outline": 2, "content": True},
    }
    snapshot = assemble_snapshot(_parts(state, slides=2))
    assert snapshot.outline_count == 2
    assert snapshot.revisions_used == 2


def test_forbidden_hits_are_phrases_and_gate_codes_are_quality() -> None:
    """Gate codes are content-quality violations, not forbidden phrases."""
    state = {
        FIELD_CURRENT_PHASE: GATE_CONTENT,
        FIELD_FORBIDDEN_PHRASES: ["Synergy"],
        FIELD_SLIDE_DRAFTS: [{"body": "This has synergy inside"}],
        FIELD_CONTENT_GATE: {
            FIELD_VIOLATIONS: [
                {FIELD_SEVERITY: SEVERITY_BLOCKER, FIELD_CODE: "banned"},
                {FIELD_SEVERITY: "warning", FIELD_CODE: "soft"},
            ]
        },
    }
    snapshot = assemble_snapshot(_parts(state, slides=1))
    assert snapshot.forbidden_hits == ("Synergy",)
    assert [item.rule for item in snapshot.quality_violations] == ["banned"]


def test_design_without_a_report_is_a_blocker() -> None:
    state = {
        FIELD_CURRENT_PHASE: GATE_DESIGN,
        FIELD_PHASE_STATUS: PHASE_STATUS_AWAITING,
    }
    snapshot = assemble_snapshot(_parts(state, images=(_IMAGE,), slides=1))
    assert snapshot.presentation_blockers == (BLOCKER_MISSING,)


def test_design_blocking_flag_and_clean_report() -> None:
    blocked = {
        FIELD_CURRENT_PHASE: GATE_DESIGN,
        FIELD_PRESENTATION_VALIDATION: {FIELD_BLOCKING: True},
    }
    clean = {
        FIELD_CURRENT_PHASE: GATE_DESIGN,
        FIELD_PRESENTATION_VALIDATION: {FIELD_BLOCKING: False, FIELD_VIOLATIONS: []},
    }
    blocked_parts = _parts(blocked, slides=1)
    clean_parts = _parts(clean, slides=1)
    assert assemble_snapshot(blocked_parts).presentation_blockers == (BLOCKER_BLOCKING,)
    assert assemble_snapshot(clean_parts).presentation_blockers == ()


def test_images_are_passed_through() -> None:
    snapshot = assemble_snapshot(_parts({}, images=(_IMAGE,), slides=1, stale=True))
    assert snapshot.images == (_IMAGE,)
    assert snapshot.stale is True
