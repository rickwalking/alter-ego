"""AE-0392: content_quality reason, measured detail, and repair-before-revise.

Domain and runner against fakes; the real engine is exercised in
tests/unit/application/test_content_quality_gate_flow_ae0392.py.

Gherkin: tests/features/autopilot_content_quality_gate_ae0392.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pytest

from rag_backend.modules.autopilot.application.feedback import (
    gate_feedback,
    measured_detail,
)
from rag_backend.modules.autopilot.application.gate_repair import (
    GateRead,
    GateRepairDependencies,
    GateRepairStep,
)
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.constants import (
    BLOCKER_BLOCKING,
    BLOCKER_MISSING,
    FIELD_BLOCKING,
    FIELD_CODE,
    FIELD_CONTENT_GATE,
    FIELD_CURRENT_PHASE,
    FIELD_PRESENTATION_VALIDATION,
    FIELD_VIOLATIONS,
    GATE_CONTENT,
    GATE_DESIGN,
    GATE_FINAL_REVIEW,
    GATE_IMAGES,
    GATE_OUTLINE,
    REASON_DESIGN,
    REASON_FORBIDDEN,
    REASON_IMAGES,
    REASON_OUTLINE,
    REASON_PERSONA_SCORE,
    REASON_READY,
    REASON_RESEARCH,
)
from rag_backend.modules.autopilot.domain.autofix import (
    AutofixStatus,
    GateRepairCommand,
    GateRepairOutcome,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateAction,
    GateSnapshot,
    PolicyDecision,
    QualityViolation,
    SnapshotParts,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.domain.quality import (
    measured_pairs,
    quality_violations,
    violation_lines,
)
from rag_backend.modules.autopilot.domain.snapshot import assemble_snapshot
from rag_backend.modules.autopilot.quality_constants import (
    MAX_MEASURED_VIOLATIONS,
    REASON_CONTENT_QUALITY,
    SLIDE_UNKNOWN,
    VIOLATION_TEXT_MAX_CHARS,
)
from rag_backend.modules.editorial.public import (
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
)
from tests.unit.modules.autopilot.test_autopilot_runner import (
    _PROJECT,
    _Editorial,
    _Notices,
    _Recovery,
    _run,
    _Runs,
    _snapshot,
    _topic,
)

_HEADING = "heading_not_sentence_case_pt"
_EMPTY = "body_empty"


def _violation(rule: str, slide: int | None = 5, **extra: object) -> dict[str, object]:
    return {FIELD_CODE: rule, "slide_index": slide, **extra}


def _quality_snapshot(
    *violations: QualityViolation, phase: str = GATE_CONTENT
) -> GateSnapshot:
    return replace(
        _snapshot(phase, 90.0, 0),
        quality_violations=violations,
        presentation_blockers=(BLOCKER_BLOCKING,) if phase == GATE_DESIGN else (),
    )


_CASING = QualityViolation(rule=_HEADING, slide_index=5, locale="pt", field="heading")


class TestQualityViolations:
    """Scenario: A presentation rule is reported as content_quality with rule@slide."""

    def test_reads_blockers_with_their_current_text(self) -> None:
        report = {
            FIELD_VIOLATIONS: [
                _violation(_HEADING, 5, locale="pt", field="heading", message="m"),
                _violation(_EMPTY, 4, locale="en", field="body"),
                _violation("soft", 3, severity="warning"),
                _violation("", 2),
                "not a dict",
            ]
        }
        state = {
            "localized_slides": [
                {"slide_index": 5, "presentation_pt": {"heading": " a heading "}},
                {"slide_index": 4, "presentation_en": "not a payload"},
                "not a slide",
                {"slide_index": "x"},
            ]
        }
        found = quality_violations(report, state)
        assert [(item.rule, item.slide_index) for item in found] == [
            (_HEADING, 5),
            (_EMPTY, 4),
        ]
        assert found[0].text == "a heading"
        assert found[0].message == "m"
        assert found[1].text == ""

    def test_carousel_wide_rule_and_unreadable_reports(self) -> None:
        found = quality_violations(
            {FIELD_VIOLATIONS: [{FIELD_CODE: "slide_count_invalid"}]}, {}
        )
        assert found[0].slide_index is None
        assert measured_pairs(found) == f"slide_count_invalid@{SLIDE_UNKNOWN}"
        assert quality_violations({FIELD_VIOLATIONS: "x"}, {}) == ()
        assert quality_violations(None, {}) == ()

    def test_no_text_without_locale_or_field(self) -> None:
        report = {FIELD_VIOLATIONS: [_violation(_HEADING, 5)]}
        state = {"localized_slides": [{"slide_index": 5, "presentation_pt": {}}]}
        assert quality_violations(report, state)[0].text == ""

    def test_measured_pairs_dedupe_and_cap_at_ten(self) -> None:
        """Scenario: Measured lists at most 10 rule@slide pairs."""
        items = tuple(QualityViolation(rule=_HEADING, slide_index=n) for n in range(12))
        pairs = measured_pairs((*items, items[0])).split(", ")
        assert len(pairs) == MAX_MEASURED_VIOLATIONS
        assert pairs[0] == f"{_HEADING}@0"
        assert len(violation_lines(items)) == MAX_MEASURED_VIOLATIONS

    def test_violation_line_names_slide_rule_and_truncated_text(self) -> None:
        text = "x" * (VIOLATION_TEXT_MAX_CHARS + 50)
        item = replace(_CASING, message="Heading must start uppercase", text=text)
        (line,) = violation_lines((item,))
        assert line.startswith(f"slide 5 (pt heading): {_HEADING}. Heading must")
        assert f'"{"x" * VIOLATION_TEXT_MAX_CHARS}"' in line
        assert "x" * (VIOLATION_TEXT_MAX_CHARS + 1) not in line


class TestSnapshotAndPolicy:
    def test_content_gate_reports_content_quality(self) -> None:
        report = {FIELD_VIOLATIONS: [_violation(_HEADING, 5), _violation(_EMPTY, 4)]}
        state = {FIELD_CURRENT_PHASE: GATE_CONTENT, FIELD_CONTENT_GATE: report}
        snapshot = assemble_snapshot(
            SnapshotParts(
                state=state, images=(), slides_total=7, lock_version=1, stale=False
            )
        )
        assert snapshot.forbidden_hits == ()
        complete = replace(
            _snapshot(GATE_CONTENT, 90.0, 0),
            quality_violations=snapshot.quality_violations,
        )
        decision = decide(complete)
        assert decision == PolicyDecision(
            action=GateAction.REVISE, reason=REASON_CONTENT_QUALITY
        )
        assert measured_detail(complete, decision.reason) == (
            f"{_HEADING}@5, {_EMPTY}@4"
        )

    def test_design_report_violations_are_content_quality(self) -> None:
        """Scenario: The design gate gets the same treatment."""
        report = {FIELD_BLOCKING: True, FIELD_VIOLATIONS: [_violation(_HEADING, 2)]}
        state = {
            FIELD_CURRENT_PHASE: GATE_DESIGN,
            FIELD_PRESENTATION_VALIDATION: report,
        }
        snapshot = assemble_snapshot(
            SnapshotParts(
                state=state, images=(), slides_total=7, lock_version=1, stale=False
            )
        )
        assert snapshot.presentation_blockers == (BLOCKER_BLOCKING,)
        assert [item.rule for item in snapshot.quality_violations] == [_HEADING]
        assert decide(_quality_snapshot(_CASING, phase=GATE_DESIGN)).reason == (
            REASON_CONTENT_QUALITY
        )

    def test_design_without_rules_stays_a_design_failure(self) -> None:
        snapshot = replace(
            _snapshot(GATE_DESIGN, 90.0, 0), presentation_blockers=(BLOCKER_MISSING,)
        )
        assert decide(snapshot).reason == REASON_DESIGN
        assert measured_detail(snapshot, REASON_DESIGN) == BLOCKER_MISSING

    def test_other_gates_read_no_quality(self) -> None:
        report = {FIELD_VIOLATIONS: [_violation(_HEADING, 2)]}
        state = {FIELD_CURRENT_PHASE: GATE_IMAGES, FIELD_CONTENT_GATE: report}
        snapshot = assemble_snapshot(
            SnapshotParts(
                state=state, images=(), slides_total=7, lock_version=1, stale=False
            )
        )
        assert snapshot.quality_violations == ()

    def test_forbidden_phrase_wins_over_quality(self) -> None:
        """Scenario: A real forbidden phrase still revises as forbidden_phrase."""
        snapshot = replace(_quality_snapshot(_CASING), forbidden_hits=("synergy",))
        decision = decide(snapshot)
        assert decision.reason == REASON_FORBIDDEN
        assert measured_detail(snapshot, REASON_FORBIDDEN) == "synergy"

    def test_final_review_stays_with_the_owner(self) -> None:
        """Scenario: Final review stays with the owner."""
        snapshot = _quality_snapshot(_CASING, phase=GATE_FINAL_REVIEW)
        assert decide(snapshot).reason == REASON_READY


class TestMeasuredDetail:
    """Measured is never empty (the prod feedback read "Measured: .")."""

    @pytest.mark.parametrize(
        ("reason", "expected"),
        [
            (REASON_PERSONA_SCORE, "90.0"),
            (REASON_RESEARCH, "3"),
            (REASON_OUTLINE, "6/6"),
            (REASON_IMAGES, "6/6"),
            ("engine_error", "engine_error"),
        ],
    )
    def test_each_reason(self, reason: str, expected: str) -> None:
        assert measured_detail(_snapshot(GATE_OUTLINE, 90.0, 0), reason) == expected

    def test_unscored_persona_falls_back_to_the_engine_blocker(self) -> None:
        snapshot = replace(
            _snapshot(GATE_CONTENT, None, 0), engine_blocker="persona_score_too_low"
        )
        assert measured_detail(snapshot, REASON_PERSONA_SCORE) == (
            "persona_score_too_low"
        )

    def test_feedback_without_violations_has_no_slide_list(self) -> None:
        text = gate_feedback(_snapshot(GATE_OUTLINE, 90.0, 0), REASON_OUTLINE)
        assert "Measured: 6/6." in text
        assert "Fix only these slides" not in text
        assert text.endswith("Keep the topic and the audience.")

    def test_feedback_lists_each_failing_slide(self) -> None:
        text = gate_feedback(_quality_snapshot(_CASING), REASON_CONTENT_QUALITY)
        assert f"Measured: {_HEADING}@5." in text
        assert f"- slide 5 (pt heading): {_HEADING}." in text


@dataclass
class _QualityEditorial(_Editorial):
    """Content gate blocking on casing until the repair clears it."""

    violations: tuple[QualityViolation, ...] = (_CASING,)

    async def read_gate(self, project_id: str) -> GateSnapshot:
        snapshot = await super().read_gate(project_id)
        return replace(snapshot, quality_violations=self.violations)


@dataclass
class _Repairer:
    status: AutofixStatus
    calls: list[GateRepairCommand] = field(default_factory=list)
    # A FIXED repair clears this gate's violations, like the real repair does.
    gate: _QualityEditorial | None = None

    async def repair_gate(self, command: GateRepairCommand) -> GateRepairOutcome:
        self.calls.append(command)
        if self.status is AutofixStatus.FIXED and self.gate is not None:
            self.gate.violations = ()
        return GateRepairOutcome(status=self.status, fixed_rules=(_HEADING,))


def _runner(
    editorial: _Editorial, runs: _Runs, repairer: _Repairer | None
) -> AutopilotRunner:
    return AutopilotRunner(
        RunnerDependencies(
            runs=runs,
            topics=runs,
            editorial=editorial,
            notices=_Notices(),
            recovery=_Recovery(runs=runs),
            owner_user_id="owner-1",
            gate_repair=repairer,
        )
    )


def _generating() -> _Runs:
    run = _run(AutopilotRunState.GENERATING, _PROJECT)
    return _Runs(run=run, topic=_topic(run.topic_candidate_id))


@pytest.mark.asyncio
class TestRepairBeforeRevise:
    async def test_conflict_waits_for_the_next_tick(self) -> None:
        """Scenario: Another writer holds the carousel during the repair."""
        editorial = _QualityEditorial(phase=GATE_CONTENT)
        repairer = _Repairer(status=AutofixStatus.CONFLICT)
        assert await _runner(editorial, _generating(), repairer).tick() == 1
        assert editorial.resumes == []
        assert repairer.calls[0].phase == GATE_CONTENT
        assert repairer.calls[0].expected_version == 4

    async def test_nothing_fixed_revises_with_the_original_read(self) -> None:
        """Scenario: A violation the repair cannot fix gets a targeted revise."""
        editorial = _QualityEditorial(phase=GATE_CONTENT)
        repairer = _Repairer(status=AutofixStatus.NOTHING_TO_FIX)
        await _runner(editorial, _generating(), repairer).tick()
        assert editorial.resumes is not None
        (command,) = editorial.resumes
        assert command.action == REVIEW_ACTION_REVISE
        assert f"{_HEADING}@5" in command.feedback

    async def test_fixed_gate_is_read_again_and_approved(self) -> None:
        """Scenario: A casing-only violation is repaired and approved."""
        editorial = _QualityEditorial(phase=GATE_CONTENT)
        repairer = _Repairer(status=AutofixStatus.FIXED, gate=editorial)
        await _runner(editorial, _generating(), repairer).tick()
        assert editorial.resumes is not None
        assert [command.action for command in editorial.resumes] == [
            REVIEW_ACTION_APPROVE
        ]
        assert editorial.revisions == 0

    async def test_passing_gate_is_not_repaired(self) -> None:
        editorial = _Editorial(phase=GATE_CONTENT)
        repairer = _Repairer(status=AutofixStatus.FIXED)
        await _runner(editorial, _generating(), repairer).tick()
        assert repairer.calls == []

    async def test_non_quality_reason_is_not_repaired(self) -> None:
        editorial = _Editorial(phase=GATE_CONTENT, score=10.0)
        repairer = _Repairer(status=AutofixStatus.FIXED)
        await _runner(editorial, _generating(), repairer).tick()
        assert repairer.calls == []

    async def test_step_skips_gates_the_validator_does_not_block(self) -> None:
        repairer = _Repairer(status=AutofixStatus.FIXED)
        step = GateRepairStep(
            GateRepairDependencies(editorial=_Editorial(), repairer=repairer)
        )
        read = GateRead(
            run=_generating().run,
            snapshot=_quality_snapshot(_CASING, phase=GATE_IMAGES),
            decision=PolicyDecision(
                action=GateAction.REVISE, reason=REASON_CONTENT_QUALITY
            ),
        )
        assert await step.apply(read) is read
        assert repairer.calls == []
