"""The autopilot step waits on an unscored judge, then escalates its own reason.

Pure: a scripted fixer and gate reader. The runner/engine flow lives in
``tests/unit/application/test_autopilot_unscored_judge_flow_ae0433.py``.

Gherkin: tests/features/autopilot_unscored_judge_ae0433.feature
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from rag_backend.domain.constants.slide_fix import PERSONA_UNSCORED_MAX_TICKS
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.autopilot.application.gate_read import GateRead
from rag_backend.modules.autopilot.autofix_constants import (
    REASON_PERSONA_JUDGE_UNAVAILABLE,
    REASON_PERSONA_RESCORE_PENDING,
    TEXT_PERSONA_JUDGE_UNAVAILABLE,
)
from rag_backend.modules.autopilot.bootstrap import AutopilotTickConfig
from rag_backend.modules.autopilot.constants import REASON_PASSED, REASON_PERSONA_SCORE
from rag_backend.modules.autopilot.domain.autofix import (
    AutofixStatus,
    SlideFixOutcome,
)
from rag_backend.modules.autopilot.domain.gate import GateAction, QualityViolation
from rag_backend.modules.autopilot.domain.messages import StatusCopy, status_text
from rag_backend.modules.autopilot.infrastructure.content_autofixer import (
    _slide_fix_outcome,
)
from rag_backend.modules.autopilot.notify_constants import KIND_ESCALATED
from rag_backend.modules.autopilot.quality_constants import REASON_CONTENT_QUALITY
from rag_backend.modules.editorial.infrastructure.carousel_slide_fix import (
    SlideFixReport,
    SlideFixSlideReport,
)
from tests.unit.modules.autopilot.test_slide_autofix_ae0401 import (
    _FAILING,
    _Fixer,
    _read,
    _snapshot,
    _step,
)

LOW = 55.0
PENDING = SlideFixOutcome(status=AutofixStatus.FIXED, unscored_slides=(3, 7))


async def _apply(outcome: SlideFixOutcome) -> GateRead:
    """The step on a gate that still reads the stale low score after the fix."""
    fixer = _Fixer(outcome)
    step, editorial = _step(fixer, _snapshot(persona_score=LOW))
    result = await step.apply(_read(REASON_PERSONA_SCORE, persona_score=LOW))
    assert result is not None
    assert editorial.reads == 1
    return result


@pytest.mark.unit
@pytest.mark.asyncio
class TestUnscoredStep:
    async def test_unscored_slides_wait_for_the_rescore(self) -> None:
        """Scenario: An unscored judge leaves the run generating."""
        result = await _apply(PENDING)
        assert result.decision.action is GateAction.WAIT
        assert result.decision.reason == REASON_PERSONA_RESCORE_PENDING

    async def test_a_judge_down_for_the_max_ticks_escalates_its_reason(self) -> None:
        """Scenario: A judge that stays unavailable escalates with its own reason."""
        result = await _apply(replace(PENDING, judge_unavailable=True))
        assert result.decision.action is GateAction.ESCALATE
        assert result.decision.reason == REASON_PERSONA_JUDGE_UNAVAILABLE
        assert result.decision.detail == (
            "- slides 3, 7: pass every rule, but the persona judge gave no voice score"
        )

    async def test_a_slide_still_failing_escalates_as_before(self) -> None:
        """Scenario: A real low score still escalates on the voice floor."""
        result = await _apply(replace(PENDING, failing=(_FAILING,)))
        assert result.decision.action is GateAction.ESCALATE
        assert result.decision.reason == REASON_PERSONA_SCORE
        assert "slide 3" in result.decision.detail

    async def test_an_unfixable_rule_escalates_as_before(self) -> None:
        result = await _apply(replace(PENDING, unfixable_rules=("slide_count",)))
        assert result.decision.reason == REASON_PERSONA_SCORE
        assert "slide_count" in result.decision.detail

    async def test_no_unscored_slide_escalates_as_before(self) -> None:
        result = await _apply(SlideFixOutcome(status=AutofixStatus.FIXED))
        assert result.decision.action is GateAction.ESCALATE
        assert result.decision.reason == REASON_PERSONA_SCORE

    async def test_a_content_quality_gate_is_not_a_judge_wait(self) -> None:
        fixer = _Fixer(PENDING)
        step, _ = _step(
            fixer, _snapshot(quality_violations=(QualityViolation(rule="x"),))
        )
        result = await step.apply(_read(REASON_CONTENT_QUALITY))
        assert result is not None
        assert result.decision.action is GateAction.ESCALATE
        assert result.decision.reason == REASON_CONTENT_QUALITY

    async def test_a_passing_gate_with_pending_rescores_waits(self) -> None:
        """Scenario: a stale PASSING score never approves."""
        fixer = _Fixer(PENDING)
        step, editorial = _step(fixer, _snapshot(pending_rescores=(3,)))
        result = await step.apply(
            _read(
                REASON_PASSED,
                action=GateAction.APPROVE,
                pending_rescores=(3,),
                persona_score=80.0,
            )
        )
        assert result is not None
        assert editorial.reads == 1
        assert result.decision.action is GateAction.WAIT
        assert result.decision.reason == REASON_PERSONA_RESCORE_PENDING

    async def test_a_rescored_pending_slide_approves(self) -> None:
        """Once the judge scores the slide, the run proceeds."""
        fixer = _Fixer(SlideFixOutcome(status=AutofixStatus.FIXED))
        step, _ = _step(fixer, _snapshot())
        result = await step.apply(
            _read(
                REASON_PASSED,
                action=GateAction.APPROVE,
                pending_rescores=(3,),
                persona_score=80.0,
            )
        )
        assert result is not None
        assert result.decision.action is GateAction.APPROVE

    async def test_a_forbidden_hit_alongside_the_voice_floor_does_not_wait(
        self,
    ) -> None:
        """The wait fires only for a sole voice-floor failure."""
        fixer = _Fixer(PENDING)
        step, _ = _step(fixer, _snapshot(forbidden_hits=("ban",)))
        result = await step.apply(_read(REASON_PERSONA_SCORE, forbidden_hits=("ban",)))
        assert result is not None
        assert result.decision.action is not GateAction.WAIT

    async def test_a_quality_rule_alongside_the_voice_floor_does_not_wait(
        self,
    ) -> None:
        """A blocking quality rule still escalates."""
        fixer = _Fixer(PENDING)
        step, _ = _step(
            fixer, _snapshot(quality_violations=(QualityViolation(rule="x"),))
        )
        result = await step.apply(_read(REASON_PERSONA_SCORE))
        assert result is not None
        assert result.decision.action is not GateAction.WAIT


def _report(*slides: SlideFixSlideReport) -> SlideFixReport:
    return SlideFixReport(status="fixed", slides=slides)


def _slide(index: int, ticks: int, fixed: bool = True) -> SlideFixSlideReport:
    return SlideFixSlideReport(
        slide_index=index,
        fixed=fixed,
        rules=(),
        text="t",
        attempts=1,
        unscored_ticks=ticks,
    )


@pytest.mark.unit
class TestSlideFixOutcome:
    def test_unscored_fixed_slides_are_listed(self) -> None:
        outcome = _slide_fix_outcome(_report(_slide(3, 1), _slide(5, 0)), 3)
        assert outcome.unscored_slides == (3,)
        assert outcome.judge_unavailable is False

    def test_the_max_ticks_marks_the_judge_unavailable(self) -> None:
        outcome = _slide_fix_outcome(_report(_slide(3, 1), _slide(7, 3)), 3)
        assert outcome.unscored_slides == (3, 7)
        assert outcome.judge_unavailable is True

    def test_an_unfixed_slide_is_failing_not_unscored(self) -> None:
        outcome = _slide_fix_outcome(_report(_slide(3, 5, fixed=False)), 3)
        assert outcome.unscored_slides == ()
        assert outcome.judge_unavailable is False
        assert [slide.slide_index for slide in outcome.failing] == [3]


@pytest.mark.unit
class TestConfigAndCopy:
    def test_the_setting_defaults_to_three_and_needs_one(self) -> None:
        field = Settings.model_fields["autopilot_persona_unscored_max_ticks"]
        assert field.default == PERSONA_UNSCORED_MAX_TICKS == 3
        settings = Settings(autopilot_persona_unscored_max_ticks=1)
        assert settings.autopilot_persona_unscored_max_ticks == 1
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            Settings(autopilot_persona_unscored_max_ticks=0)

    def test_the_tick_config_defaults_to_the_constant(self) -> None:
        config = AutopilotTickConfig(
            owner_user_id="o", engine_factory=lambda: None, stale_after_seconds=1
        )
        assert config.persona_unscored_max_ticks == PERSONA_UNSCORED_MAX_TICKS

    def test_the_owner_reads_why_the_run_stopped(self) -> None:
        copy = StatusCopy(
            reason=REASON_PERSONA_JUDGE_UNAVAILABLE,
            link="",
            permalink="",
            days_remaining=None,
            detail="- slides 3",
        )
        text = status_text(KIND_ESCALATED, copy)
        assert TEXT_PERSONA_JUDGE_UNAVAILABLE in text
        assert "- slides 3" in text
