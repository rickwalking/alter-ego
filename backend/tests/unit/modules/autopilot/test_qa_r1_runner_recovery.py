"""Runner recovery and policy/engine alignment (QA round 1, B1/H3).

Gherkin: tests/features/autopilot_runner.feature
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

import pytest

from rag_backend.domain.constants.carousel_workflow import (
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_PRESENTATION_VALIDATION_BLOCKED,
)
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.constants import (
    FIELD_CURRENT_PHASE,
    FIELD_OVERALL,
    FIELD_PERSONA_SCORES,
    FIELD_PRESENTATION_VALIDATION,
    GATE_CONTENT,
    GATE_DESIGN,
    GATE_FINAL_REVIEW,
    REASON_DESIGN,
    REASON_PERSONA_SCORE,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateAction,
    GateSnapshot,
    ResumeCommand,
    ResumeResult,
    StartCommand,
    StartStatus,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.notice_log import NoticeLog, ReviewRecord
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.notify_constants import (
    REASON_NOTIFIER_UNCONFIGURED,
)
from rag_backend.modules.autopilot.recovery_constants import (
    REASON_OWNER_EXPIRED,
    REASON_OWNER_FIXED,
    REASON_REVIEW_REOPENED,
)
from rag_backend.modules.editorial.public import content_approve_blocker
from tests.unit.modules.autopilot.project_inputs_fake import FakeProjectInputs
from tests.unit.modules.autopilot.test_autopilot_runner import (
    _OWNER,
    _PROJECT,
    _Editorial,
    _Notices,
    _Recovery,
    _run,
    _Runs,
    _snapshot,
    _topic,
)

_NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


class _Clock:
    def now(self) -> datetime:
        return _NOW


@dataclass
class _Raising(_Editorial):
    """Editorial whose resume/start raise the real engine error type."""

    error: BaseException | None = None

    async def resume(self, command: ResumeCommand) -> ResumeResult:
        assert self.error is not None
        raise self.error

    async def start(self, command: StartCommand) -> StartStatus:
        assert self.error is not None
        raise self.error


@dataclass
class _AtFinal(_Editorial):
    """Editorial parked at final review with a chosen lock version."""

    version: int = 6

    async def read_gate(self, project_id: str) -> GateSnapshot:
        snapshot = _snapshot(GATE_FINAL_REVIEW, 90.0, 0)
        return replace(snapshot, lock_version=self.version)


def _runner(
    runs: _Runs,
    editorial: _Editorial,
    notices: _Notices,
    configured: bool = True,
) -> tuple[AutopilotRunner, _Recovery]:
    recovery = _Recovery(runs=runs)
    runner = AutopilotRunner(
        RunnerDependencies(
            runs=runs,
            topics=runs,
            editorial=editorial,
            notices=notices,
            recovery=recovery,
            owner_user_id=_OWNER,
            inputs=FakeProjectInputs(),
            notifier_configured=configured,
            clock=_Clock(),
        )
    )
    return runner, recovery


# Scenario: The engine and the policy read a missing "overall" the same way
def test_engine_check_skips_a_missing_overall() -> None:
    state: dict[str, object] = {
        FIELD_CURRENT_PHASE: GATE_CONTENT,
        FIELD_PERSONA_SCORES: {"voice": {FIELD_OVERALL: 90}, "tone": {}},
    }
    assert content_approve_blocker(state) is None


# Scenario: A stored overall is read on the 0-100 scale (AE-0407)
def test_engine_check_reads_a_ten_point_overall_on_hundred() -> None:
    passing: dict[str, object] = {
        FIELD_CURRENT_PHASE: GATE_CONTENT,
        FIELD_PERSONA_SCORES: {"slide_1": {FIELD_OVERALL: 8.7}},
    }
    low: dict[str, object] = {
        FIELD_CURRENT_PHASE: GATE_CONTENT,
        FIELD_PERSONA_SCORES: {"slide_1": {FIELD_OVERALL: 6.5}},
    }
    assert content_approve_blocker(passing) is None
    assert content_approve_blocker(low) == ERR_PERSONA_SCORE_TOO_LOW


# Scenario: Content approve with blocking presentation violations is revised
def test_engine_check_reports_presentation_blockers_on_content() -> None:
    state: dict[str, object] = {
        FIELD_CURRENT_PHASE: GATE_CONTENT,
        FIELD_PERSONA_SCORES: {"voice": {FIELD_OVERALL: 90}},
        FIELD_PRESENTATION_VALIDATION: {"blocking": True},
    }
    assert content_approve_blocker(state) == ERR_PRESENTATION_VALIDATION_BLOCKED


def test_engine_check_passes_outside_content() -> None:
    state: dict[str, object] = {
        FIELD_CURRENT_PHASE: GATE_DESIGN,
        FIELD_PERSONA_SCORES: {"voice": {}},
    }
    assert content_approve_blocker(state) is None


@pytest.mark.parametrize(
    ("blocker", "reason"),
    [
        (ERR_PRESENTATION_VALIDATION_BLOCKED, REASON_DESIGN),
        (ERR_PERSONA_SCORE_TOO_LOW, REASON_PERSONA_SCORE),
        ("some_new_engine_rule", "engine_error"),
    ],
)
def test_policy_revises_when_the_engine_would_refuse(blocker: str, reason: str) -> None:
    snapshot = replace(_snapshot(GATE_CONTENT, 90.0, 0), engine_blocker=blocker)
    decision = decide(snapshot)
    assert decision.action is GateAction.REVISE
    assert decision.reason == reason
    capped = decide(replace(snapshot, revisions_used=2))
    assert capped.action is GateAction.ESCALATE


# Scenario: Design is revised at most once
def test_design_escalates_after_one_revise() -> None:
    snapshot = replace(
        _snapshot(GATE_DESIGN, 90.0, 0), presentation_blockers=("overflow",)
    )
    assert decide(snapshot).action is GateAction.REVISE
    assert decide(replace(snapshot, revisions_used=1)).action is GateAction.ESCALATE
    content = replace(_snapshot(GATE_CONTENT, 50.0, 1))
    assert decide(content).action is GateAction.REVISE


# Scenario: An unclassified engine error escalates the run instead of looping
@pytest.mark.asyncio
async def test_unclassified_resume_error_escalates_once() -> None:
    run = _run(AutopilotRunState.GENERATING, _PROJECT)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    editorial = _Raising(
        phase=GATE_CONTENT, error=ValueError(ERR_PERSONA_SCORE_TOO_LOW)
    )
    runner, recovery = _runner(runs, editorial, _Notices())

    assert await runner.tick() == 1

    assert recovery.rollbacks == 1
    assert runs.run.state is AutopilotRunState.ESCALATED
    assert runs.run.state_reason is not None
    assert runs.run.state_reason.startswith("engine_error:ValueError:")
    assert recovery.marks[-1].version == 4
    assert await runner.tick() == 0


# Scenario: An unclassified start error fails the queued run
@pytest.mark.asyncio
async def test_unclassified_start_error_fails_the_queued_run() -> None:
    run = _run(AutopilotRunState.QUEUED)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    editorial = _Raising(error=RuntimeError("graph exploded"))
    runner, recovery = _runner(runs, editorial, _Notices())

    assert await runner.tick() == 1

    assert recovery.rollbacks == 1
    assert runs.run.state is AutopilotRunState.FAILED
    assert runs.run.state_reason == "engine_error:RuntimeError:graph exploded"


# Scenario: 72 hour expiry
@pytest.mark.asyncio
@pytest.mark.parametrize(("hours", "expired"), [(73, True), (71, False)])
async def test_awaiting_owner_expires_after_72_hours(hours: int, expired: bool) -> None:
    run = replace(
        _run(AutopilotRunState.AWAITING_OWNER, _PROJECT),
        updated_at=_NOW - timedelta(hours=hours),
    )
    runs = _Runs(run=run, topic=None)
    runner, _recovery = _runner(runs, _Editorial(), _Notices())

    moved = await runner.tick()

    if expired:
        assert moved == 1
        assert runs.run.state is AutopilotRunState.EXPIRED
        assert runs.run.state_reason == REASON_OWNER_EXPIRED
        return
    assert moved == 0
    assert runs.run.state is AutopilotRunState.AWAITING_OWNER


# Scenario: An escalated run the owner fixed in the web UI returns to the owner
@pytest.mark.asyncio
async def test_fixed_escalation_returns_to_the_owner() -> None:
    run = replace(_run(AutopilotRunState.ESCALATED, _PROJECT), escalated_version=4)
    runs = _Runs(run=run, topic=None)
    notices = _Notices()
    runner, _recovery = _runner(runs, _AtFinal(version=6), notices)

    assert await runner.tick() == 1

    assert runs.run.state is AutopilotRunState.AWAITING_OWNER
    assert runs.run.state_reason == REASON_OWNER_FIXED
    assert [event.revision for event in notices.events] == [6]


# Scenario: An escalated run whose carousel did not change stays escalated
@pytest.mark.asyncio
async def test_unchanged_escalation_stays_escalated() -> None:
    run = replace(_run(AutopilotRunState.ESCALATED, _PROJECT), escalated_version=6)
    runs = _Runs(run=run, topic=None)
    notices = _Notices()
    runner, _recovery = _runner(runs, _AtFinal(version=6), notices)

    assert await runner.tick() == 0
    assert runs.run.state is AutopilotRunState.ESCALATED
    assert notices.events == []


@pytest.mark.asyncio
async def test_already_reviewed_revision_reopens_with_the_keyboard_only() -> None:
    reviewed = NoticeLog(
        reviews=(ReviewRecord(revision=6, album_ids=(1, 2), keyboard_id=3),)
    )
    run = replace(_run(AutopilotRunState.ESCALATED, _PROJECT), notice_log=reviewed)
    runs = _Runs(run=run, topic=None)
    notices = _Notices()
    runner, _recovery = _runner(runs, _AtFinal(version=6), notices)

    assert await runner.tick() == 1
    assert runs.run.state is AutopilotRunState.AWAITING_OWNER
    assert runs.run.state_reason == REASON_REVIEW_REOPENED
    assert notices.events == []


@pytest.mark.asyncio
async def test_unconfigured_notifier_escalation_wakes_once_configured() -> None:
    run = replace(
        _run(AutopilotRunState.ESCALATED, _PROJECT),
        state_reason=REASON_NOTIFIER_UNCONFIGURED,
        escalated_version=6,
    )
    runs = _Runs(run=run, topic=None)
    asleep, _ = _runner(runs, _AtFinal(version=6), _Notices(), configured=False)
    assert await asleep.tick() == 0
    awake, _ = _runner(runs, _AtFinal(version=6), _Notices())
    assert await awake.tick() == 1
    assert runs.run.state is AutopilotRunState.AWAITING_OWNER
