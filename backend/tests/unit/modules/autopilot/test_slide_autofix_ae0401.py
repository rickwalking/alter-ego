"""The autopilot model-fix step and its escalation copy (pure).

Gherkin: tests/features/autopilot_slide_autofix_ae0401.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from uuid import uuid4

import pytest

from rag_backend.modules.autopilot.application.gate_read import GateRead
from rag_backend.modules.autopilot.application.slide_autofix import (
    SlideAutofixDependencies,
    SlideAutofixStep,
    escalation_detail,
    needs_model_fix,
)
from rag_backend.modules.autopilot.constants import (
    GATE_CONTENT,
    GATE_RESEARCH,
    PAYLOAD_DETAIL,
    PHASE_STATUS_AWAITING,
    REASON_PERSONA_SCORE,
    REASON_RESEARCH,
)
from rag_backend.modules.autopilot.domain.autofix import (
    AutofixStatus,
    FailingSlide,
    SlideFixCommand,
    SlideFixOutcome,
)
from rag_backend.modules.autopilot.domain.escalation_detail import detail_of
from rag_backend.modules.autopilot.domain.gate import (
    GateAction,
    GateSnapshot,
    PolicyDecision,
    QualityViolation,
)
from rag_backend.modules.autopilot.domain.messages import StatusCopy, status_text
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    _state_changed_record,
)
from rag_backend.modules.autopilot.notify_constants import KIND_ESCALATED
from rag_backend.modules.autopilot.quality_constants import REASON_CONTENT_QUALITY

_LONG = "Eu reviso PRs de agentes toda semana " * 10


def _snapshot(**changes: object) -> GateSnapshot:
    base = GateSnapshot(
        phase=GATE_CONTENT,
        phase_status=PHASE_STATUS_AWAITING,
        lock_version=4,
        sources=(),
        outline_count=9,
        slides_total=9,
        persona_score=None,
        forbidden_hits=(),
        presentation_blockers=(),
        images=(),
        revisions_used=0,
        stale=False,
    )
    return replace(base, **changes)


def _run() -> AutopilotRun:
    return AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=uuid4(),
        carousel_project_id="p1",
        state=AutopilotRunState.GENERATING,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )


def _read(
    reason: str, action: GateAction = GateAction.REVISE, **changes: object
) -> GateRead:
    return GateRead(
        run=_run(),
        snapshot=_snapshot(**changes),
        decision=PolicyDecision(action=action, reason=reason),
    )


@dataclass
class _Fixer:
    outcome: SlideFixOutcome
    commands: list[SlideFixCommand] = field(default_factory=list)

    async def fix_slides(self, command: SlideFixCommand) -> SlideFixOutcome:
        self.commands.append(command)
        return self.outcome


@dataclass
class _Editorial:
    snapshot: GateSnapshot
    reads: int = 0

    async def read_gate(self, project_id: str) -> GateSnapshot:
        del project_id
        self.reads += 1
        return self.snapshot


def _step(
    fixer: _Fixer | None, snapshot: GateSnapshot
) -> tuple[SlideAutofixStep, _Editorial]:
    editorial = _Editorial(snapshot=snapshot)
    deps = SlideAutofixDependencies(editorial=editorial, fixer=fixer)
    return SlideAutofixStep(deps), editorial


_FAILING = FailingSlide(
    slide_index=3, rules=("markup_leak", "copy_truncated"), text=_LONG, attempts=3
)


@pytest.mark.unit
class TestNeedsModelFix:
    @pytest.mark.parametrize(
        ("reason", "action", "phase", "expected"),
        [
            (REASON_CONTENT_QUALITY, GateAction.REVISE, GATE_CONTENT, True),
            (REASON_PERSONA_SCORE, GateAction.ESCALATE, GATE_CONTENT, True),
            (REASON_CONTENT_QUALITY, GateAction.APPROVE, GATE_CONTENT, False),
            (REASON_RESEARCH, GateAction.REVISE, GATE_CONTENT, False),
            (REASON_CONTENT_QUALITY, GateAction.REVISE, GATE_RESEARCH, False),
        ],
    )
    def test_only_quality_gates_and_reasons(
        self, reason: str, action: GateAction, phase: str, expected: bool
    ) -> None:
        assert needs_model_fix(_read(reason, action, phase=phase)) is expected


@pytest.mark.unit
class TestEscalationDetail:
    def test_lists_rules_text_and_attempts(self) -> None:
        detail = escalation_detail(
            SlideFixOutcome(
                status=AutofixStatus.NOTHING_TO_FIX,
                failing=(_FAILING,),
                unfixable_rules=("slide_count_invalid",),
            )
        )
        lines = detail.splitlines()
        assert lines[0] == "Autofix could not fix these slides:"
        assert lines[1].startswith("- slide 3: markup_leak, copy_truncated.")
        assert lines[1].endswith('..." (3 fix attempts)')
        assert len(lines[1]) < 220
        assert lines[2] == "- carousel: slide_count_invalid (no slide fix possible)"

    def test_short_text_is_not_clipped(self) -> None:
        slide = replace(_FAILING, text="Curto.\n Demais.")
        assert 'Current text: "Curto. Demais."' in escalation_detail(
            SlideFixOutcome(status=AutofixStatus.FIXED, failing=(slide,))
        )

    def test_nothing_failing_is_empty(self) -> None:
        assert escalation_detail(SlideFixOutcome(status=AutofixStatus.FIXED)) == ""


@pytest.mark.unit
@pytest.mark.asyncio
class TestSlideAutofixStep:
    async def test_without_a_fixer_the_read_is_unchanged(self) -> None:
        read = _read(REASON_CONTENT_QUALITY)
        step, _ = _step(None, read.snapshot)
        assert await step.apply(read) is read

    async def test_other_reasons_are_not_fixed(self) -> None:
        fixer = _Fixer(SlideFixOutcome(status=AutofixStatus.FIXED))
        read = _read(REASON_RESEARCH)
        step, _ = _step(fixer, read.snapshot)
        assert await step.apply(read) is read
        assert fixer.commands == []

    async def test_conflict_waits_for_the_next_tick(self) -> None:
        fixer = _Fixer(SlideFixOutcome(status=AutofixStatus.CONFLICT))
        read = _read(REASON_CONTENT_QUALITY)
        step, editorial = _step(fixer, read.snapshot)
        assert await step.apply(read) is None
        assert editorial.reads == 0
        assert fixer.commands[0].expected_version == 4

    async def test_fixed_and_clean_is_approved(self) -> None:
        fixer = _Fixer(SlideFixOutcome(status=AutofixStatus.FIXED))
        step, editorial = _step(fixer, _snapshot(lock_version=5))
        result = await step.apply(
            _read(
                REASON_CONTENT_QUALITY, quality_violations=(QualityViolation(rule="x"),)
            )
        )
        assert result is not None
        assert result.decision.action is GateAction.APPROVE
        assert editorial.reads == 1

    async def test_nothing_fixable_escalates_without_a_reread(self) -> None:
        fixer = _Fixer(
            SlideFixOutcome(
                status=AutofixStatus.NOTHING_TO_FIX,
                unfixable_rules=("slide_count_invalid",),
            )
        )
        read = _read(REASON_CONTENT_QUALITY)
        step, editorial = _step(fixer, read.snapshot)
        result = await step.apply(read)
        assert result is not None
        assert result.decision.action is GateAction.ESCALATE
        assert result.decision.reason == REASON_CONTENT_QUALITY
        assert "slide_count_invalid" in result.decision.detail
        assert editorial.reads == 0

    async def test_low_voice_left_escalates_as_persona_score(self) -> None:
        fixer = _Fixer(SlideFixOutcome(status=AutofixStatus.FIXED, failing=(_FAILING,)))
        step, _ = _step(fixer, _snapshot(persona_score=40.0))
        result = await step.apply(_read(REASON_PERSONA_SCORE, persona_score=40.0))
        assert result is not None
        assert result.decision.action is GateAction.ESCALATE
        assert result.decision.reason == REASON_PERSONA_SCORE
        assert "slide 3" in result.decision.detail


@pytest.mark.unit
class TestEscalationCopy:
    def test_state_changed_event_carries_the_detail(self) -> None:
        command = TransitionCommand(
            run_id=uuid4(),
            expected=AutopilotRunState.GENERATING,
            new=AutopilotRunState.ESCALATED,
            reason=REASON_CONTENT_QUALITY,
            detail="Autofix could not fix these slides:",
        )
        payload = _state_changed_record(command).payload
        assert detail_of(payload) == "Autofix could not fix these slides:"
        plain = _state_changed_record(replace(command, detail="")).payload
        assert PAYLOAD_DETAIL not in plain
        assert detail_of(plain) == ""
        assert detail_of({PAYLOAD_DETAIL: 3}) == ""

    @pytest.mark.parametrize("link", ["", "https://x/carousels/p1"])
    def test_telegram_escalation_lists_the_slides(self, link: str) -> None:
        copy = StatusCopy(
            reason=REASON_CONTENT_QUALITY,
            link=link,
            permalink="",
            days_remaining=None,
            detail="- slide 3: markup_leak",
        )
        text = status_text(KIND_ESCALATED, copy)
        assert text.startswith(f"Escalated: {REASON_CONTENT_QUALITY}\n- slide 3")
        assert text.endswith(link or "markup_leak")

    def test_escalation_without_detail_is_unchanged(self) -> None:
        copy = StatusCopy(
            reason="run_stale", link="", permalink="", days_remaining=None
        )
        assert status_text(KIND_ESCALATED, copy) == "Escalated: run_stale"
