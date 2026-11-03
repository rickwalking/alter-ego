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
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.constants import (
    REASON_READY,
    REASON_RENDER_PENDING,
    RENDER_PENDING_MAX_SECONDS,
)
from rag_backend.modules.autopilot.cover_constants import (
    REASON_COVER_REVIEW_REOPENED,
    REASON_RENDER_STUCK,
    REOPEN_RECOVERY_GRACE_SECONDS,
)
from rag_backend.modules.autopilot.domain.gate import GateAction, GateSnapshot
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
)
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.domain.render_wait import RenderFacts, render_facts
from rag_backend.modules.autopilot.domain.schedule_ports import DueScheduleQuery
from rag_backend.modules.autopilot.schedule_constants import SCHEDULE_SCAN_LIMIT
from tests.unit.modules.autopilot.project_inputs_fake import FakeProjectInputs
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_cover_review_hold_ae0594 import (
    _NOW,
    _FixedClock,
    _run,
    _Store,
)
from tests.unit.modules.autopilot.test_owner_actions import (
    _Notices,
    _snapshot,
    _Topics,
    _world,
)

_S = AutopilotRunState
_AHEAD = _NOW + timedelta(hours=3)
_SETTLED = _NOW - timedelta(seconds=REOPEN_RECOVERY_GRACE_SECONDS + 1)


@dataclass
class _Scheduled:
    store: _Store
    padding: int = 0

    async def due(self, query: DueScheduleQuery) -> list[AutopilotRun]:
        del query
        return []

    async def waiting(self, query: DueScheduleQuery) -> list[AutopilotRun]:
        """``padding`` approved runs come first, so the store's run is last."""
        others = [
            replace(_run(_S.SCHEDULED), carousel_project_id=f"other-{n}")
            for n in range(self.padding)
        ]
        run = self.store.run
        mine = (
            [run]
            if run is not None
            and run.state is _S.SCHEDULED
            and run.scheduled_at is not None
            and run.scheduled_at > query.now
            else []
        )
        listed = [*others, *mine]
        return listed[query.offset : query.offset + query.limit]


@dataclass
class _Reviews:
    reopened_ids: frozenset[str]

    async def reopened(self, project_id: str) -> bool:
        return project_id in self.reopened_ids


def _recovery(store: _Store, reopened: bool, padding: int = 0) -> ReopenRecovery:
    ids = frozenset({"p-1"}) if reopened else frozenset()
    return ReopenRecovery(
        ReopenRecoveryDeps(
            runs=store,
            scheduled=_Scheduled(store, padding=padding),
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

    # Scenario: A lost review request is recovered
    @pytest.mark.asyncio
    async def test_a_run_past_the_first_page_is_not_starved(self) -> None:
        store = _scheduled(_SETTLED)

        recovery = _recovery(store, reopened=True, padding=SCHEDULE_SCAN_LIMIT + 3)

        assert await recovery.tick() == 1
        assert store.run is not None
        assert store.run.state is _S.REWORKING


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

    # Scenario: The new Telegram review waits for the render
    def test_a_render_that_never_lands_is_escalated(self) -> None:
        stuck = replace(_snapshot(), render_pending=True, render_overdue=True)

        decision = decide(stuck)

        assert decision.action is GateAction.ESCALATE
        assert decision.reason == REASON_RENDER_STUCK

    # Scenario: The new Telegram review waits for the render
    def test_render_facts_bound_the_wait(self) -> None:
        limit = timedelta(seconds=RENDER_PENDING_MAX_SECONDS)

        assert render_facts(None, _NOW) == RenderFacts(pending=False, overdue=False)
        fresh = render_facts(_NOW - timedelta(minutes=1), _NOW)
        assert fresh == RenderFacts(pending=True, overdue=False)
        naive = (_NOW - limit).replace(tzinfo=None)
        assert render_facts(naive, _NOW) == RenderFacts(pending=True, overdue=True)


@pytest.mark.unit
class TestApprovedOnTheWebsite:
    # Scenario: A run whose carousel was approved on the website goes back to the owner
    def test_an_approved_final_review_stops_for_the_owner(self) -> None:
        approved = replace(_snapshot(), phase_status="approved")

        decision = decide(approved)

        assert decision.action is GateAction.STOP
        assert decision.reason == REASON_READY

    # Scenario: A run whose carousel was approved on the website goes back to the owner
    @pytest.mark.asyncio
    async def test_the_runner_hands_a_reworking_run_back_with_a_review(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world = _world()
        world.runs.run = replace(world.runs.run, state=_S.REWORKING)
        approved = replace(_snapshot(), phase_status="approved")

        async def _read_gate(project_id: str) -> GateSnapshot:
            del project_id
            return approved

        monkeypatch.setattr(world.editorial, "read_gate", _read_gate)
        notices = _Notices()
        runner = AutopilotRunner(
            RunnerDependencies(
                runs=world.runs,
                topics=_Topics(),
                editorial=world.editorial,
                notices=notices,
                recovery=_Recovery(runs=world.runs),
                owner_user_id="owner",
                inputs=FakeProjectInputs(),
            )
        )

        await runner.tick()

        assert world.runs.run.state is _S.AWAITING_OWNER
        assert len(notices.ready) == 1
