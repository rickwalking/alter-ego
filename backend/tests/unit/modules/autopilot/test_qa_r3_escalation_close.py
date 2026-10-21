"""An escalation close never drops a carousel the owner fixed (QA r3 Q3).

Gherkin: tests/features/autopilot_runner.feature
  Scenario: A fixed escalation is woken, never closed
  Scenario: A fixed escalation without a notifier is recorded before it closes
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from uuid import UUID

import pytest

from rag_backend.modules.autopilot.application.run_recovery import (
    RecoveryDependencies,
    RunRecovery,
)
from rag_backend.modules.autopilot.domain.gate import GateSnapshot
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.recovery import UnnotifiedMark
from rag_backend.modules.autopilot.notify_constants import (
    REASON_NOTIFIER_UNCONFIGURED,
)
from rag_backend.modules.autopilot.recovery_constants import (
    ESCALATED_SCAN_LIMIT,
    OWNER_REVIEW_EXPIRY_HOURS,
    REASON_ESCALATION_EXPIRED,
    REASON_OWNER_FIXED,
)
from tests.unit.modules.autopilot.test_autopilot_runner import _Notices
from tests.unit.modules.autopilot.test_qa_r2_escalation import (
    _NOW,
    _escalated,
    _final,
    _ManyRuns,
    _PerProject,
    _RotatingRecovery,
)

_OLD = OWNER_REVIEW_EXPIRY_HOURS + 1
_ESCALATED_AT = 4
_FIXED_AT = 6


class _MovingClock:
    def __init__(self) -> None:
        self.current = _NOW

    def now(self) -> datetime:
        return self.current


@dataclass
class _Runs(_ManyRuns):
    clock: _MovingClock = field(default_factory=_MovingClock)


@dataclass
class _Recovery(_RotatingRecovery):
    unnotified: list[UnnotifiedMark] = field(default_factory=list)

    async def mark_unnotified(self, mark: UnnotifiedMark) -> bool:
        self.unnotified.append(mark)
        run = self.runs.items[mark.run_id]
        if run.state is not AutopilotRunState.ESCALATED:
            return False
        self.runs.items[mark.run_id] = replace(
            run, state_reason=REASON_NOTIFIER_UNCONFIGURED, updated_at=mark.at
        )
        return True


@dataclass
class _Failing(_PerProject):
    broken: set[str] = field(default_factory=set)

    async def read_gate(self, project_id: str) -> GateSnapshot:
        if project_id in self.broken:
            raise RuntimeError("editorial down")
        return await super().read_gate(project_id)


def _recovery(
    runs: _Runs, editorial: _PerProject, configured: bool
) -> tuple[RunRecovery, _Recovery]:
    store = _Recovery(runs=runs)
    recovery = RunRecovery(
        RecoveryDependencies(
            runs=runs,
            editorial=editorial,
            notices=_Notices(),
            recovery=store,
            clock=runs.clock,
            notifier_configured=configured,
        )
    )
    return recovery, store


def _old_fixed(runs: _Runs, editorial: _PerProject, index: int) -> AutopilotRun:
    run = _escalated(index, hours_ago=_OLD, escalated_version=_ESCALATED_AT)
    runs.items[run.run_id] = run
    editorial.snapshots[f"project-{index}"] = _final(_FIXED_AT)
    return run


def _states(runs: _Runs, ids: list[UUID]) -> set[AutopilotRunState]:
    return {runs.items[run_id].state for run_id in ids}


# Scenario: A fixed escalation is woken, never closed
@pytest.mark.asyncio
async def test_an_old_fixed_escalation_is_woken_not_closed() -> None:
    runs, editorial = _Runs(), _PerProject()
    run = _old_fixed(runs, editorial, 0)
    recovery, _ = _recovery(runs, editorial, configured=True)

    assert await recovery.sweep() == 1

    stored = runs.items[run.run_id]
    assert stored.state is AutopilotRunState.AWAITING_OWNER
    assert stored.state_reason == REASON_OWNER_FIXED


# Scenario: A fixed escalation is woken, never closed
@pytest.mark.asyncio
async def test_a_fixed_escalation_past_the_wake_scan_is_not_closed() -> None:
    runs, editorial = _Runs(), _PerProject()
    ids = [
        _old_fixed(runs, editorial, index).run_id
        for index in range(ESCALATED_SCAN_LIMIT + 1)
    ]
    recovery, _ = _recovery(runs, editorial, configured=True)

    await recovery.sweep()

    assert AutopilotRunState.REJECTED not in _states(runs, ids)
    await recovery.sweep()
    assert _states(runs, ids) == {AutopilotRunState.AWAITING_OWNER}


@pytest.mark.asyncio
async def test_an_unreadable_carousel_is_not_closed() -> None:
    runs, editorial = _Runs(), _Failing(broken={"project-0"})
    run = _escalated(0, hours_ago=_OLD, escalated_version=_ESCALATED_AT)
    runs.items[run.run_id] = run
    recovery, _ = _recovery(runs, editorial, configured=True)

    assert await recovery.sweep() == 0

    assert runs.items[run.run_id].state is AutopilotRunState.ESCALATED


# Scenario: A fixed escalation without a notifier is recorded before it closes
@pytest.mark.asyncio
async def test_a_fixed_escalation_without_a_notifier_is_recorded_then_closed() -> None:
    runs, editorial = _Runs(), _PerProject()
    run = _old_fixed(runs, editorial, 0)
    recovery, store = _recovery(runs, editorial, configured=False)

    assert await recovery.sweep() == 0
    recorded = runs.items[run.run_id]
    assert recorded.state is AutopilotRunState.ESCALATED
    assert recorded.state_reason == REASON_NOTIFIER_UNCONFIGURED
    assert recorded.updated_at == _NOW
    assert await recovery.sweep() == 0
    assert len(store.unnotified) == 1

    runs.clock.current = _NOW + timedelta(hours=_OLD)
    assert await recovery.sweep() == 1
    closed = runs.items[run.run_id]
    assert closed.state is AutopilotRunState.REJECTED
    assert closed.state_reason == REASON_ESCALATION_EXPIRED


@pytest.mark.asyncio
async def test_a_recorded_unnotified_run_wakes_when_the_notifier_returns() -> None:
    runs, editorial = _Runs(), _PerProject()
    run = _old_fixed(runs, editorial, 0)
    unconfigured, _ = _recovery(runs, editorial, configured=False)
    await unconfigured.sweep()

    configured, _ = _recovery(runs, editorial, configured=True)
    assert await configured.sweep() == 1

    assert runs.items[run.run_id].state is AutopilotRunState.AWAITING_OWNER


@pytest.mark.asyncio
async def test_an_unfixed_notifier_unconfigured_escalation_still_closes() -> None:
    runs, editorial = _Runs(), _PerProject()
    run = replace(
        _escalated(0, hours_ago=_OLD, escalated_version=_ESCALATED_AT),
        state_reason=REASON_NOTIFIER_UNCONFIGURED,
    )
    runs.items[run.run_id] = run
    editorial.snapshots["project-0"] = _final(_ESCALATED_AT)
    recovery, store = _recovery(runs, editorial, configured=False)

    assert await recovery.sweep() == 1

    assert runs.items[run.run_id].state is AutopilotRunState.REJECTED
    assert store.unnotified == []
