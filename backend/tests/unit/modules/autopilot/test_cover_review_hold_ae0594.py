"""The Telegram review hold of a website cover switch, and the worker.

Gherkin: tests/features/website_cover_review_switch_ae0594.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from rag_backend.modules.autopilot.application.cover_review_hold import (
    CoverReviewHold,
    CoverReviewHoldDeps,
)
from rag_backend.modules.autopilot.cover_constants import (
    COVER_REVIEW_HOLD_PHASE,
    REASON_COVER_REVIEW_HOLD,
    REASON_COVER_REVIEW_KEPT,
)
from rag_backend.modules.autopilot.domain.cover_hold import (
    hold_active,
    hold_started,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.recovery import ReworkIntent
from tests.unit.modules.autopilot.test_owner_actions import (
    _Notices,
    _runner,
    _World,
    _world,
)

_S = AutopilotRunState
_PROJECT = "p-1"
_NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
_ANCHOR = _NOW - timedelta(hours=60)


class _FixedClock:
    def now(self) -> datetime:
        return _NOW


def _run(state: AutopilotRunState) -> AutopilotRun:
    return AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=uuid4(),
        carousel_project_id=_PROJECT,
        state=state,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
        updated_at=_ANCHOR,
    )


@dataclass
class _Store:
    """Runs, rework intents and commits in memory; ``updated_at`` like the repo."""

    run: AutopilotRun | None
    lose: bool = False
    commits: int = 0
    queued: list[ReworkIntent] = field(default_factory=list)

    async def find_by_carousel(self, project_id: str) -> AutopilotRun | None:
        assert project_id == _PROJECT
        return self.run

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        return self.run if self.run is not None and self.run.run_id == run_id else None

    async def transition(self, command: TransitionCommand) -> bool:
        if self.lose or self.run is None or self.run.state is not command.expected:
            return False
        self.run = replace(
            self.run,
            state=command.new,
            state_reason=command.reason,
            updated_at=command.updated_at or _NOW,
        )
        return True

    async def queue_rework(self, intent: ReworkIntent) -> bool:
        assert self.run is not None
        self.queued.append(intent)
        self.run = replace(
            self.run, rework_phase=intent.phase, rework_feedback=intent.feedback
        )
        return True

    async def clear_rework(self, run_id: UUID) -> None:
        assert self.run is not None and self.run.run_id == run_id
        self.run = replace(self.run, rework_phase=None, rework_feedback=None)

    async def commit(self) -> None:
        self.commits += 1


def _hold(store: _Store) -> CoverReviewHold:
    return CoverReviewHold(
        CoverReviewHoldDeps(
            runs=store, recovery=store, checkpoint=store, clock=_FixedClock()
        )
    )


@pytest.mark.unit
class TestCoverReviewHold:
    # Scenario: The Telegram review is held while slide 1 changes
    @pytest.mark.asyncio
    async def test_hold_takes_the_run_out_of_the_owners_review(self) -> None:
        store = _Store(run=_run(_S.AWAITING_OWNER))

        held = await _hold(store).hold(_PROJECT)

        assert store.run is not None
        assert held == store.run.run_id
        assert store.run.state is _S.REWORKING
        assert store.run.state_reason == REASON_COVER_REVIEW_HOLD
        assert store.run.rework_phase == COVER_REVIEW_HOLD_PHASE
        assert hold_started(store.run.rework_feedback) == _NOW
        assert store.run.updated_at == _ANCHOR
        assert store.commits == 1

    # Scenario: The Telegram review is held while slide 1 changes
    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [_S.SCHEDULED, _S.PUBLISHED, _S.REWORKING])
    async def test_only_a_run_awaiting_the_owner_is_held(
        self, state: AutopilotRunState
    ) -> None:
        store = _Store(run=_run(state))

        assert await _hold(store).hold(_PROJECT) is None
        assert store.run is not None and store.run.state is state
        assert store.queued == []

    # Scenario: The Telegram review is held while slide 1 changes
    @pytest.mark.asyncio
    async def test_no_run_or_a_lost_race_holds_nothing(self) -> None:
        assert await _hold(_Store(run=None)).hold(_PROJECT) is None
        lost = _Store(run=_run(_S.AWAITING_OWNER), lose=True)
        assert await _hold(lost).hold(_PROJECT) is None
        assert lost.queued == []

    # Scenario: The Telegram review is held while slide 1 changes
    @pytest.mark.asyncio
    async def test_changed_release_leaves_the_resend_to_the_worker(self) -> None:
        store = _Store(run=_run(_S.AWAITING_OWNER))
        held = await _hold(store).hold(_PROJECT)
        assert held is not None

        await _hold(store).release(held, changed=True)

        assert store.run is not None
        assert store.run.state is _S.REWORKING
        assert store.run.rework_phase is None
        assert store.commits == 2

    # Scenario: A cover the owner chose while the job ran wins on a completed carousel
    @pytest.mark.asyncio
    async def test_unchanged_release_hands_back_the_review_and_its_window(self) -> None:
        store = _Store(run=_run(_S.AWAITING_OWNER))
        held = await _hold(store).hold(_PROJECT)
        assert held is not None

        await _hold(store).release(held, changed=False)

        assert store.run is not None
        assert store.run.state is _S.AWAITING_OWNER
        assert store.run.state_reason == REASON_COVER_REVIEW_KEPT
        assert store.run.rework_phase is None
        assert store.run.updated_at == _ANCHOR


def _held(world: _World, started: datetime | None) -> None:
    world.runs.run = replace(
        world.runs.run,
        state=_S.REWORKING,
        rework_phase=COVER_REVIEW_HOLD_PHASE,
        rework_feedback=started.isoformat() if started else None,
    )


@pytest.mark.unit
class TestWorkerResend:
    # Scenario: The Telegram review is held while slide 1 changes
    @pytest.mark.asyncio
    async def test_a_held_run_is_skipped_then_sent_again(self) -> None:
        world = _world()
        notices = _Notices()
        _held(world, datetime.now(UTC))

        assert await _runner(world, notices).tick() == 0
        assert world.runs.run.state is _S.REWORKING
        assert notices.ready == []

        world.runs.run = replace(world.runs.run, rework_phase=None)
        await _runner(world, notices).tick()

        assert world.runs.run.state is _S.AWAITING_OWNER
        assert [event.revision for event in notices.ready] == [4]

    # Scenario: A Telegram review hold that outlives its task is dropped
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "started",
        [datetime.now(UTC) - timedelta(hours=1), None],
        ids=["old", "undated"],
    )
    async def test_an_outlived_hold_is_dropped_and_sent(
        self, started: datetime | None
    ) -> None:
        world = _world()
        notices = _Notices()
        _held(world, started)

        await _runner(world, notices).tick()

        assert world.runs.run.rework_phase is None
        assert world.runs.run.state is _S.AWAITING_OWNER
        assert [event.revision for event in notices.ready] == [4]

    # Scenario: A held run does not block the other autopilot runs
    @pytest.mark.asyncio
    async def test_the_runner_steps_the_next_run_past_a_held_one(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world = _world()
        held = replace(
            world.runs.run,
            run_id=uuid4(),
            state=_S.REWORKING,
            rework_phase=COVER_REVIEW_HOLD_PHASE,
            rework_feedback=datetime.now(UTC).isoformat(),
        )
        other = replace(world.runs.run, state=_S.REWORKING)
        world.runs.run = other
        listed: list[RunListQuery] = []

        async def _both(query: RunListQuery) -> list[AutopilotRun]:
            listed.append(query)
            return [held, other] if query.state is _S.REWORKING else []

        monkeypatch.setattr(world.runs, "list_by_state", _both)
        notices = _Notices()

        await _runner(world, notices).tick()

        assert world.runs.run.state is _S.AWAITING_OWNER
        assert [event.run_id for event in notices.ready] == [other.run_id]

    # Scenario: A Telegram review hold that outlives its task is dropped
    def test_hold_activity(self) -> None:
        run = _run(_S.REWORKING)
        assert hold_active(run, _NOW) is False
        assert hold_started("not a time") is None
        assert hold_started(None) is None
        fresh = replace(
            run, rework_phase=COVER_REVIEW_HOLD_PHASE, rework_feedback=_NOW.isoformat()
        )
        assert hold_active(fresh, _NOW + timedelta(minutes=5)) is True
        assert hold_active(fresh, _NOW + timedelta(hours=1)) is False
