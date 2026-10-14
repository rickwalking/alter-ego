"""Escalated runs: fair wake scan and closing abandoned runs (AE-0348 QA r2 R1).

Gherkin: tests/features/autopilot_runner.feature
  Scenario: A fixed escalation wakes even behind five abandoned ones
  Scenario: An escalation nobody fixes is closed after 72 hours
  Scenario: An escalation whose carousel was rejected is closed
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from rag_backend.modules.autopilot.application.run_recovery import (
    RecoveryDependencies,
    RunRecovery,
)
from rag_backend.modules.autopilot.constants import (
    EVENT_TYPE_STATE_CHANGED,
    GATE_FINAL_REVIEW,
    PAYLOAD_REASON,
    PAYLOAD_STATE,
)
from rag_backend.modules.autopilot.domain.gate import GateSnapshot
from rag_backend.modules.autopilot.domain.messages import (
    StatusCopy,
    notice_kind,
    status_text,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.recovery import (
    EscalatedScan,
    EscalationMark,
    ReworkIntent,
    WakeCheck,
)
from rag_backend.modules.autopilot.notify_constants import KIND_ESCALATION_CLOSED
from rag_backend.modules.autopilot.recovery_constants import (
    ESCALATED_SCAN_LIMIT,
    OWNER_REVIEW_EXPIRY_HOURS,
    REASON_CAROUSEL_REJECTED,
    REASON_ESCALATION_EXPIRED,
    REASON_OWNER_FIXED,
)
from rag_backend.modules.autopilot.webhook_constants import REASON_OWNER_REJECTED
from rag_backend.modules.editorial.public import PHASE_STATUS_REJECTED
from tests.unit.modules.autopilot.test_autopilot_runner import (
    _Editorial,
    _Notices,
    _run,
    _snapshot,
)

_NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
_FIXED_VERSION = 6
_ABANDONED = ESCALATED_SCAN_LIMIT


class _Clock:
    def now(self) -> datetime:
        return _NOW


@dataclass
class _ManyRuns:
    """The run-repository calls ``RunRecovery`` makes, over several runs."""

    items: dict[UUID, AutopilotRun] = field(default_factory=dict)

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        return self.items.get(run_id)

    async def list_by_state(self, query: RunListQuery) -> list[AutopilotRun]:
        matching = [run for run in self.items.values() if run.state is query.state]
        matching.sort(key=lambda run: run.updated_at or _NOW)
        return matching[: query.limit]

    async def transition(self, command: TransitionCommand) -> bool:
        run = self.items.get(command.run_id)
        if run is None or run.state is not command.expected:
            return False
        self.items[command.run_id] = replace(
            run, state=command.new, state_reason=command.reason, updated_at=_NOW
        )
        return True


@dataclass
class _RotatingRecovery:
    """``RunRecoveryStore`` whose escalated scan rotates by last check time."""

    runs: _ManyRuns
    checked: dict[UUID, datetime] = field(default_factory=dict)

    async def escalated_for_check(self, scan: EscalatedScan) -> list[AutopilotRun]:
        escalated = [
            run
            for run in self.runs.items.values()
            if run.state is AutopilotRunState.ESCALATED
        ]
        escalated.sort(key=self._order)
        return escalated[: scan.limit]

    def _order(self, run: AutopilotRun) -> tuple[bool, datetime, datetime]:
        last = self.checked.get(run.run_id)
        return (last is not None, last or _NOW, run.updated_at or _NOW)

    async def mark_checked(self, check: WakeCheck) -> None:
        self.checked[check.run_id] = check.at

    async def queue_rework(self, intent: ReworkIntent) -> bool:
        return True

    async def clear_rework(self, run_id: UUID) -> None:
        return None

    async def mark_escalated(self, mark: EscalationMark) -> None:
        return None

    async def rollback(self) -> None:
        return None


@dataclass
class _PerProject(_Editorial):
    """Editorial at final review; each project has its own snapshot."""

    snapshots: dict[str, GateSnapshot] = field(default_factory=dict)

    async def read_gate(self, project_id: str) -> GateSnapshot:
        return self.snapshots[project_id]


def _final(version: int, status: str | None = None) -> GateSnapshot:
    snapshot = replace(_snapshot(GATE_FINAL_REVIEW, 90.0, 0), lock_version=version)
    if status is None:
        return snapshot
    return replace(snapshot, phase_status=status)


def _escalated(index: int, hours_ago: float, escalated_version: int) -> AutopilotRun:
    project = f"project-{index}"
    run = _run(AutopilotRunState.ESCALATED, project)
    return replace(
        run,
        escalated_version=escalated_version,
        updated_at=_NOW - timedelta(hours=hours_ago),
    )


def _recovery(
    runs: _ManyRuns, editorial: _PerProject, configured: bool = True
) -> RunRecovery:
    return RunRecovery(
        RecoveryDependencies(
            runs=runs,
            editorial=editorial,
            notices=_Notices(),
            recovery=_RotatingRecovery(runs=runs),
            clock=_Clock(),
            notifier_configured=configured,
        )
    )


# Scenario: A fixed escalation wakes even behind five abandoned ones
@pytest.mark.asyncio
async def test_newest_fixed_escalation_wakes_behind_abandoned_ones() -> None:
    runs = _ManyRuns()
    editorial = _PerProject()
    for index in range(_ABANDONED):
        run = _escalated(index, hours_ago=48 - index, escalated_version=_FIXED_VERSION)
        runs.items[run.run_id] = run
        editorial.snapshots[f"project-{index}"] = _final(_FIXED_VERSION)
    newest = _escalated(_ABANDONED, hours_ago=1, escalated_version=4)
    runs.items[newest.run_id] = newest
    editorial.snapshots[f"project-{_ABANDONED}"] = _final(_FIXED_VERSION)
    recovery = _recovery(runs, editorial)

    first = await recovery.sweep()
    second = await recovery.sweep()

    woken = runs.items[newest.run_id]
    assert (first, second) == (0, 1)
    assert woken.state is AutopilotRunState.AWAITING_OWNER
    assert woken.state_reason == REASON_OWNER_FIXED
    abandoned = [run for run in runs.items.values() if run.run_id != newest.run_id]
    assert {run.state for run in abandoned} == {AutopilotRunState.ESCALATED}


# Scenario: An escalation nobody fixes is closed after 72 hours
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("hours_ago", "closed"),
    [(OWNER_REVIEW_EXPIRY_HOURS + 1, True), (OWNER_REVIEW_EXPIRY_HOURS - 1, False)],
)
async def test_abandoned_escalation_is_rejected_after_72_hours(
    hours_ago: int, closed: bool
) -> None:
    run = _escalated(0, hours_ago=hours_ago, escalated_version=_FIXED_VERSION)
    runs = _ManyRuns(items={run.run_id: run})
    editorial = _PerProject(snapshots={"project-0": _final(_FIXED_VERSION)})

    moved = await _recovery(runs, editorial).sweep()

    stored = runs.items[run.run_id]
    if closed:
        assert moved == 1
        assert stored.state is AutopilotRunState.REJECTED
        assert stored.state_reason == REASON_ESCALATION_EXPIRED
        return
    assert moved == 0
    assert stored.state is AutopilotRunState.ESCALATED


# Scenario: An escalation whose carousel was rejected is closed
@pytest.mark.asyncio
@pytest.mark.parametrize("configured", [True, False])
async def test_rejected_carousel_closes_the_escalation(configured: bool) -> None:
    run = _escalated(0, hours_ago=2, escalated_version=4)
    runs = _ManyRuns(items={run.run_id: run})
    rejected = _final(_FIXED_VERSION, PHASE_STATUS_REJECTED)
    editorial = _PerProject(snapshots={"project-0": rejected})

    moved = await _recovery(runs, editorial, configured=configured).sweep()

    stored = runs.items[run.run_id]
    assert moved == 1
    assert stored.state is AutopilotRunState.REJECTED
    assert stored.state_reason == REASON_CAROUSEL_REJECTED


# Scenario: An escalation nobody fixes is closed after 72 hours
@pytest.mark.parametrize("reason", [REASON_ESCALATION_EXPIRED, REASON_CAROUSEL_REJECTED])
def test_closed_escalation_tells_the_owner(reason: str) -> None:
    payload = {PAYLOAD_STATE: AutopilotRunState.REJECTED.value, PAYLOAD_REASON: reason}

    kind = notice_kind(EVENT_TYPE_STATE_CHANGED, payload)
    text = status_text(
        KIND_ESCALATION_CLOSED,
        StatusCopy(reason=reason, link="", permalink="", days_remaining=None),
    )

    assert kind == KIND_ESCALATION_CLOSED
    assert reason in text


def test_owner_reject_on_telegram_sends_no_extra_notice() -> None:
    payload = {
        PAYLOAD_STATE: AutopilotRunState.REJECTED.value,
        PAYLOAD_REASON: REASON_OWNER_REJECTED,
    }
    assert notice_kind(EVENT_TYPE_STATE_CHANGED, payload) is None
