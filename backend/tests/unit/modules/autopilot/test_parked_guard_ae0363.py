"""Parked-workflow guard: reconcile, policy, and runner re-drive (AE-0363).

Gherkin: tests/features/autopilot_runner.feature (AE-0363 scenarios)
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pytest

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_APPROVED_HOLD,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_REJECTED,
)
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.constants import (
    GATE_CONTENT,
    GATE_FINAL_REVIEW,
    PHASE_STATUS_AWAITING,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    REASON_PHASE_FAILED,
    REASON_RUN_STALE,
    REASON_WAITING,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateAction,
    GateSnapshot,
    RedriveCommand,
    ResumeCommand,
    ResumeResult,
    ResumeStatus,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.parked import (
    GateStatus,
    GateStatusInput,
    RowRun,
    reconcile_gate_status,
)
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.parked_constants import REASON_ENGINE_PARKED
from tests.unit.modules.autopilot.project_inputs_fake import FakeProjectInputs
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

_GRACE = 600


def _status(
    engine_status: str,
    row: RowRun | None,
    engine_phase: str = GATE_CONTENT,
) -> GateStatus:
    return reconcile_gate_status(
        GateStatusInput(
            engine_phase=engine_phase,
            engine_status=engine_status,
            row=row,
            grace_seconds=_GRACE,
        )
    )


def test_run_in_flight_wins_over_the_checkpoint() -> None:
    """Scenario: A run in flight on the row makes the policy wait."""
    row = RowRun(phase_status=PHASE_STATUS_IN_PROGRESS, idle_seconds=9999)
    assert _status(PHASE_STATUS_AWAITING, row) == GateStatus(
        phase_status=PHASE_STATUS_IN_PROGRESS
    )
    assert _status(PHASE_STATUS_APPROVED, row).parked is False


def test_awaiting_and_failed_checkpoints_are_taken_as_is() -> None:
    row = RowRun(phase_status=PHASE_STATUS_FAILED, idle_seconds=1)
    assert _status(PHASE_STATUS_AWAITING, row).phase_status == PHASE_STATUS_AWAITING
    assert _status(PHASE_STATUS_FAILED, None).phase_status == PHASE_STATUS_FAILED


def test_a_failed_row_behind_an_approved_checkpoint_is_a_failure() -> None:
    """Scenario: A phase that failed after its gate was approved escalates."""
    row = RowRun(phase_status=PHASE_STATUS_FAILED, idle_seconds=1)
    assert _status(PHASE_STATUS_APPROVED, row) == GateStatus(
        phase_status=PHASE_STATUS_FAILED
    )


def test_prod_shape_is_parked_and_overdue_after_the_grace() -> None:
    """Scenario: carousel 8e350d6e (row outline/awaiting, checkpoint approved)."""
    fresh = RowRun(phase_status=PHASE_STATUS_AWAITING, idle_seconds=_GRACE)
    old = RowRun(phase_status=PHASE_STATUS_AWAITING, idle_seconds=_GRACE + 1)
    assert _status(PHASE_STATUS_APPROVED, fresh) == GateStatus(
        phase_status=PHASE_STATUS_APPROVED, parked=True, parked_overdue=False
    )
    assert _status(PHASE_STATUS_APPROVED, old).parked_overdue is True


def test_unknown_row_age_counts_as_overdue() -> None:
    unknown = RowRun(phase_status=PHASE_STATUS_AWAITING, idle_seconds=None)
    assert _status(PHASE_STATUS_APPROVED, unknown).parked_overdue is True
    assert _status(PHASE_STATUS_APPROVED, None).parked_overdue is True


def test_held_or_final_carousels_are_never_parked() -> None:
    row = RowRun(phase_status=PHASE_STATUS_APPROVED, idle_seconds=99999)
    for phase in (GATE_FINAL_REVIEW, PHASE_APPROVED_HOLD):
        status = _status(PHASE_STATUS_APPROVED, row, engine_phase=phase)
        assert status == GateStatus(phase_status=PHASE_STATUS_APPROVED)


def _parked(status: str, overdue: bool, **extra: object) -> GateSnapshot:
    base = _snapshot(GATE_CONTENT, 90.0, 0)
    return replace(
        base,
        phase_status=status,
        parked=True,
        parked_overdue=overdue,
        **extra,
    )


def test_policy_waits_redrives_or_escalates_a_parked_workflow() -> None:
    """Scenario: The policy never waits on a parked workflow past the grace."""
    waiting = decide(_parked(PHASE_STATUS_APPROVED, overdue=False))
    assert (waiting.action, waiting.reason) == (GateAction.WAIT, REASON_WAITING)
    for status in (PHASE_STATUS_APPROVED, PHASE_STATUS_IN_PROGRESS):
        redrive = decide(_parked(status, overdue=True))
        assert (redrive.action, redrive.reason) == (
            GateAction.REDRIVE,
            REASON_ENGINE_PARKED,
        )
    rejected = decide(_parked(PHASE_STATUS_REJECTED, overdue=True))
    assert (rejected.action, rejected.reason) == (
        GateAction.ESCALATE,
        REASON_ENGINE_PARKED,
    )


def test_stale_and_failed_still_win_over_parked() -> None:
    stale = decide(_parked(PHASE_STATUS_APPROVED, overdue=True, stale=True))
    assert stale.reason == REASON_RUN_STALE
    failed = decide(_parked(PHASE_STATUS_FAILED, overdue=True))
    assert failed.reason == REASON_PHASE_FAILED


@dataclass
class _ParkedEditorial(_Editorial):
    """The fake gate is parked; ``redrive`` returns ``redrive_status``."""

    redrive_status: ResumeStatus = ResumeStatus.APPLIED
    redrives: list[RedriveCommand] = field(default_factory=list)

    async def read_gate(self, project_id: str) -> GateSnapshot:
        return _parked(PHASE_STATUS_APPROVED, overdue=True)

    async def resume(self, command: ResumeCommand) -> ResumeResult:
        raise AssertionError("a parked workflow is never resumed")

    async def redrive(self, command: RedriveCommand) -> ResumeResult:
        self.redrives.append(command)
        return ResumeResult(status=self.redrive_status)


def _runner_for(editorial: _ParkedEditorial) -> tuple[AutopilotRunner, _Runs]:
    run = _run(AutopilotRunState.GENERATING, _PROJECT)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    runner = AutopilotRunner(
        RunnerDependencies(
            runs=runs,
            topics=runs,
            editorial=editorial,
            notices=_Notices(),
            recovery=_Recovery(runs=runs),
            owner_user_id="owner-1",
            inputs=FakeProjectInputs(),
        )
    )
    return runner, runs


@pytest.mark.asyncio
async def test_runner_redrives_a_parked_workflow_once_per_tick() -> None:
    """Scenario: The runner re-drives a parked workflow, sending no review."""
    editorial = _ParkedEditorial()
    runner, runs = _runner_for(editorial)

    assert await runner.tick() == 1

    assert editorial.redrives == [
        RedriveCommand(project_id=_PROJECT, expected_version=4, phase=GATE_CONTENT)
    ]
    assert runs.run.state is AutopilotRunState.GENERATING


@pytest.mark.asyncio
async def test_runner_escalates_when_nothing_is_parked() -> None:
    """Scenario: A re-drive that finds nothing parked escalates with a reason."""
    editorial = _ParkedEditorial(redrive_status=ResumeStatus.NOT_PARKED)
    runner, runs = _runner_for(editorial)

    assert await runner.tick() == 1

    assert runs.run.state is AutopilotRunState.ESCALATED
    assert runs.run.state_reason == REASON_ENGINE_PARKED
