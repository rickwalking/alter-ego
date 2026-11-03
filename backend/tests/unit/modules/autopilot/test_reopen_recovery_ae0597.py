"""A lost review request is recovered, and the final review waits for a render.

Gherkin: tests/features/reopen_review_on_cover_switch_ae0597.feature
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

import pytest

from rag_backend.modules.autopilot.application.reopen_recovery import (
    ReopenRecovery,
    ReopenRecoveryDeps,
)
from rag_backend.modules.autopilot.constants import (
    REASON_READY,
    REASON_RENDER_PENDING,
)
from rag_backend.modules.autopilot.cover_constants import (
    REASON_COVER_REVIEW_REOPENED,
    REOPEN_RECOVERY_GRACE_SECONDS,
)
from rag_backend.modules.autopilot.domain.gate import GateAction
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
)
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.domain.schedule_ports import DueScheduleQuery
from tests.unit.modules.autopilot.test_cover_review_hold_ae0594 import (
    _NOW,
    _FixedClock,
    _run,
    _Store,
)
from tests.unit.modules.autopilot.test_owner_actions import _snapshot

_S = AutopilotRunState
_AHEAD = _NOW + timedelta(hours=3)
_SETTLED = _NOW - timedelta(seconds=REOPEN_RECOVERY_GRACE_SECONDS + 1)


@dataclass
class _Scheduled:
    store: _Store

    async def due(self, query: DueScheduleQuery) -> list[AutopilotRun]:
        del query
        return []

    async def waiting(self, query: DueScheduleQuery) -> list[AutopilotRun]:
        run = self.store.run
        if run is None or run.state is not _S.SCHEDULED:
            return []
        at = run.scheduled_at
        return [run] if at is not None and at > query.now else []


@dataclass
class _Reviews:
    reopened_ids: frozenset[str]

    async def reopened(self, project_id: str) -> bool:
        return project_id in self.reopened_ids


def _recovery(store: _Store, reopened: bool) -> ReopenRecovery:
    ids = frozenset({"p-1"}) if reopened else frozenset()
    return ReopenRecovery(
        ReopenRecoveryDeps(
            runs=store,
            scheduled=_Scheduled(store),
            reviews=_Reviews(ids),
            checkpoint=store,
            clock=_FixedClock(),
        )
    )


def _scheduled(updated_at: datetime) -> _Store:
    run = replace(_run(_S.SCHEDULED), scheduled_at=_AHEAD, updated_at=updated_at)
    return _Store(run=run)


@pytest.mark.unit
class TestReopenRecovery:
    # Scenario: A lost review request is recovered
    @pytest.mark.asyncio
    async def test_a_lost_request_sends_the_run_back_for_review(self) -> None:
        store = _scheduled(_SETTLED)

        assert await _recovery(store, reopened=True).tick() == 1

        assert store.run is not None
        assert store.run.state is _S.REWORKING
        assert store.run.state_reason == REASON_COVER_REVIEW_REOPENED
        assert store.run.updated_at == _SETTLED
        assert store.commits == 1

    # Scenario: A lost review request is recovered
    @pytest.mark.asyncio
    async def test_an_approved_carousel_keeps_its_schedule(self) -> None:
        store = _scheduled(_SETTLED)

        assert await _recovery(store, reopened=False).tick() == 0

        assert store.run is not None
        assert store.run.state is _S.SCHEDULED

    # Scenario: Approving the new review keeps the scheduled time
    @pytest.mark.asyncio
    async def test_a_schedule_tap_still_approving_is_left_alone(self) -> None:
        """The tap claims ``scheduled`` before its approve lands."""
        store = _scheduled(_NOW - timedelta(seconds=30))

        assert await _recovery(store, reopened=True).tick() == 0

        assert store.run is not None
        assert store.run.state is _S.SCHEDULED

    # Scenario: A lost review request is recovered
    @pytest.mark.asyncio
    async def test_a_run_without_a_carousel_is_skipped(self) -> None:
        store = _scheduled(_SETTLED)
        assert store.run is not None
        store.run = replace(store.run, carousel_project_id=None)

        assert await _recovery(store, reopened=True).tick() == 0


@pytest.mark.unit
class TestRenderPending:
    # Scenario: The new Telegram review waits for the render
    def test_the_final_review_waits_for_the_render(self) -> None:
        pending = replace(_snapshot(), render_pending=True)

        decision = decide(pending)

        assert decision.action is GateAction.WAIT
        assert decision.reason == REASON_RENDER_PENDING

    # Scenario: The new Telegram review waits for the render
    def test_a_rendered_final_review_stops_for_the_owner(self) -> None:
        decision = decide(_snapshot())

        assert decision.action is GateAction.STOP
        assert decision.reason == REASON_READY

    # Scenario: The new Telegram review waits for the render
    def test_an_earlier_gate_ignores_the_marker(self) -> None:
        content = replace(_snapshot(), phase="content", render_pending=True)

        assert decide(content).reason != REASON_RENDER_PENDING
