"""An abandoned escalation that closes also settles its carousel.

Feature: tests/features/escalation_close_settles_carousel_ae0601.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from rag_backend.bootstrap.autopilot_worker_factory import autopilot_tick_config
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.autopilot.bootstrap import runner_dependencies

from rag_backend.modules.autopilot.application.run_recovery import (
    RecoveryDependencies,
    RunRecovery,
)
from rag_backend.modules.autopilot.constants import GATE_CONTENT
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.recovery import CarouselSettle
from rag_backend.modules.autopilot.infrastructure.carousel_settler import (
    EditorialCarouselSettler,
)
from rag_backend.modules.autopilot.recovery_constants import (
    LOG_ESCALATION_CAROUSEL_SETTLED,
    LOG_ESCALATION_SETTLE_FAILED,
    OWNER_REVIEW_EXPIRY_HOURS,
    REASON_ESCALATION_EXPIRED,
)
from tests.unit.modules.autopilot.test_autopilot_runner import _Notices, _snapshot
from tests.unit.modules.autopilot.test_qa_r2_escalation import (
    _Clock,
    _escalated,
    _ManyRuns,
    _PerProject,
    _RotatingRecovery,
)

_OLD = OWNER_REVIEW_EXPIRY_HOURS + 1
_VERSION = 4
_PROJECT = "project-0"


@dataclass
class _Settler:
    """Records each settle; answers ``moved`` or raises ``error``."""

    moved: bool = True
    error: Exception | None = None
    calls: list[CarouselSettle] = field(default_factory=list)

    async def settle_abandoned(self, settle: CarouselSettle) -> bool:
        self.calls.append(settle)
        if self.error is not None:
            raise self.error
        return self.moved


@dataclass
class _LosingRuns(_ManyRuns):
    """Another worker moves every run first: each transition is refused."""

    async def transition(self, command: TransitionCommand) -> bool:
        del command
        return False


def _abandoned(runs: _ManyRuns, editorial: _PerProject) -> AutopilotRun:
    """An escalation older than 72 hours whose carousel waits at the content gate."""
    run = _escalated(0, hours_ago=_OLD, escalated_version=_VERSION)
    runs.items[run.run_id] = run
    editorial.snapshots[_PROJECT] = _snapshot(GATE_CONTENT, 90.0, 0)
    return run


def _recovery(
    runs: _ManyRuns, editorial: _PerProject, settler: _Settler | None
) -> RunRecovery:
    return RunRecovery(
        RecoveryDependencies(
            runs=runs,
            editorial=editorial,
            notices=_Notices(),
            recovery=_RotatingRecovery(runs=runs),
            clock=_Clock(),
            notifier_configured=True,
            carousels=settler,
        )
    )


def _closed(runs: _ManyRuns, run: AutopilotRun) -> bool:
    stored = runs.items[run.run_id]
    return (stored.state, stored.state_reason) == (
        AutopilotRunState.REJECTED,
        REASON_ESCALATION_EXPIRED,
    )


# Scenario: Closing an abandoned escalation rejects its waiting carousel
@pytest.mark.asyncio
async def test_closing_an_abandoned_escalation_settles_its_carousel() -> None:
    runs, editorial, settler = _ManyRuns(), _PerProject(), _Settler()
    run = _abandoned(runs, editorial)

    with capture_logs() as logs:
        assert await _recovery(runs, editorial, settler).sweep() == 1

    assert _closed(runs, run)
    assert settler.calls == [
        CarouselSettle(
            project_id=_PROJECT,
            expected_version=_VERSION,
            idle_hours=OWNER_REVIEW_EXPIRY_HOURS,
        )
    ]
    events = [entry["event"] for entry in logs]
    assert LOG_ESCALATION_CAROUSEL_SETTLED in events


# Scenario: A carousel that is no longer waiting for a human is left alone
# Scenario: A carousel changed since the escalation is left alone
@pytest.mark.asyncio
async def test_a_carousel_the_settler_refuses_still_closes_the_run() -> None:
    runs, editorial, settler = _ManyRuns(), _PerProject(), _Settler(moved=False)
    run = _abandoned(runs, editorial)

    with capture_logs() as logs:
        assert await _recovery(runs, editorial, settler).sweep() == 1

    assert _closed(runs, run)
    assert len(settler.calls) == 1
    events = [entry["event"] for entry in logs]
    assert LOG_ESCALATION_CAROUSEL_SETTLED not in events


# Scenario: A run without a carousel or an escalation version settles nothing
@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["carousel", "version"])
async def test_a_run_without_a_carousel_or_version_settles_nothing(
    missing: str,
) -> None:
    runs, editorial, settler = _ManyRuns(), _PerProject(), _Settler()
    run = _abandoned(runs, editorial)
    changed = (
        replace(run, carousel_project_id=None)
        if missing == "carousel"
        else replace(run, escalated_version=None)
    )
    runs.items[run.run_id] = changed

    assert await _recovery(runs, editorial, settler).sweep() == 1

    assert _closed(runs, run)
    assert settler.calls == []


# Scenario: A second sweep does nothing
@pytest.mark.asyncio
async def test_a_second_sweep_settles_nothing() -> None:
    runs, editorial, settler = _ManyRuns(), _PerProject(), _Settler()
    run = _abandoned(runs, editorial)
    recovery = _recovery(runs, editorial, settler)

    assert await recovery.sweep() == 1
    assert await recovery.sweep() == 0

    assert _closed(runs, run)
    assert len(settler.calls) == 1


# Scenario: A failed carousel settle still closes the run
@pytest.mark.asyncio
async def test_a_failed_settle_still_closes_the_run_and_is_logged() -> None:
    runs, editorial = _ManyRuns(), _PerProject()
    settler = _Settler(error=RuntimeError("carousel row locked"))
    run = _abandoned(runs, editorial)

    with capture_logs() as logs:
        assert await _recovery(runs, editorial, settler).sweep() == 1

    assert _closed(runs, run)
    failed = [e for e in logs if e["event"] == LOG_ESCALATION_SETTLE_FAILED]
    assert len(failed) == 1
    assert failed[0]["run_id"] == str(run.run_id)
    assert failed[0]["project_id"] == _PROJECT


# Scenario: A run whose close loses the race settles nothing
@pytest.mark.asyncio
async def test_a_lost_close_settles_nothing() -> None:
    runs, editorial, settler = _LosingRuns(), _PerProject(), _Settler()
    run = _abandoned(runs, editorial)

    assert await _recovery(runs, editorial, settler).sweep() == 0

    assert runs.items[run.run_id].state is AutopilotRunState.ESCALATED
    assert settler.calls == []


# Scenario: A failed carousel settle still closes the run
@pytest.mark.asyncio
async def test_without_a_settler_the_run_still_closes() -> None:
    runs, editorial = _ManyRuns(), _PerProject()
    run = _abandoned(runs, editorial)

    assert await _recovery(runs, editorial, None).sweep() == 1

    assert _closed(runs, run)


# Scenario: Closing an abandoned escalation rejects its waiting carousel
@pytest.mark.asyncio
async def test_the_worker_wires_the_carousel_settler(db_session: AsyncSession) -> None:
    config = autopilot_tick_config(Settings(credentials_encryption_key=""), MagicMock())

    settler = runner_dependencies(db_session, config).carousels

    assert isinstance(settler, EditorialCarouselSettler)
