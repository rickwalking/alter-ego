"""The Telegram side of a website cover switching slide 1 in final review.

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
    ANSWER_REVIEW_REPLACED,
    COVER_REVIEW_HOLD_PHASE,
    REASON_COVER_REVIEW_HOLD,
    REASON_COVER_REVIEW_KEPT,
    TEXT_REVIEW_REPLACED,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.notice_log import NoticeLog, ReviewRecord
from rag_backend.modules.autopilot.domain.recovery import ReworkIntent
from rag_backend.modules.autopilot.domain.review_replaced import is_replaced_review
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from tests.unit.modules.autopilot.test_owner_actions import (
    _action,
    _handle,
    _Notices,
    _runner,
    _tap,
    _World,
    _world,
)

_S = AutopilotRunState
_PROJECT = "p-1"


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
    )


@dataclass
class _Store:
    """Runs, rework intents and commits in memory."""

    run: AutopilotRun | None
    lose: bool = False
    commits: int = 0
    queued: list[ReworkIntent] = field(default_factory=list)

    async def find_by_carousel(self, project_id: str) -> AutopilotRun | None:
        assert project_id == _PROJECT
        return self.run

    async def transition(self, command: TransitionCommand) -> bool:
        if self.lose or self.run is None or self.run.state is not command.expected:
            return False
        self.run = replace(self.run, state=command.new, state_reason=command.reason)
        return True

    async def queue_rework(self, intent: ReworkIntent) -> bool:
        assert self.run is not None
        self.queued.append(intent)
        self.run = replace(self.run, rework_phase=intent.phase)
        return True

    async def clear_rework(self, run_id: UUID) -> None:
        assert self.run is not None and self.run.run_id == run_id
        self.run = replace(self.run, rework_phase=None)

    async def commit(self) -> None:
        self.commits += 1


def _hold(store: _Store) -> CoverReviewHold:
    return CoverReviewHold(
        CoverReviewHoldDeps(runs=store, recovery=store, checkpoint=store)
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
    async def test_unchanged_release_hands_the_review_back(self) -> None:
        store = _Store(run=_run(_S.AWAITING_OWNER))
        held = await _hold(store).hold(_PROJECT)
        assert held is not None

        await _hold(store).release(held, changed=False)

        assert store.run is not None
        assert store.run.state is _S.AWAITING_OWNER
        assert store.run.state_reason == REASON_COVER_REVIEW_KEPT
        assert store.run.rework_phase is None


def _held(world: _World, at: datetime) -> None:
    world.runs.run = replace(
        world.runs.run,
        state=_S.REWORKING,
        rework_phase=COVER_REVIEW_HOLD_PHASE,
        updated_at=at,
    )


@pytest.mark.unit
class TestWorkerResend:
    # Scenario: The Telegram review is held while slide 1 changes
    @pytest.mark.asyncio
    async def test_a_held_run_waits_then_is_sent_again(self) -> None:
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
        "at", [datetime.now(UTC) - timedelta(hours=1), None], ids=["old", "unknown"]
    )
    async def test_an_outlived_hold_is_dropped_and_sent(
        self, at: datetime | None
    ) -> None:
        world = _world()
        notices = _Notices()
        world.runs.run = replace(
            world.runs.run,
            state=_S.REWORKING,
            rework_phase=COVER_REVIEW_HOLD_PHASE,
            updated_at=at,
        )

        await _runner(world, notices).tick()

        assert world.runs.run.rework_phase is None
        assert world.runs.run.state is _S.AWAITING_OWNER
        assert [event.revision for event in notices.ready] == [4]


def _two_reviews(world: _World) -> None:
    world.runs.run = replace(
        world.runs.run,
        notice_log=NoticeLog(
            reviews=(
                ReviewRecord(revision=4, album_ids=(1,), keyboard_id=9),
                ReviewRecord(revision=6, album_ids=(2,), keyboard_id=20),
            )
        ),
    )


def _on(update: WebhookUpdate, message_id: int) -> WebhookUpdate:
    return replace(update, message_id=message_id)


@pytest.mark.unit
class TestReplacedReview:
    # Scenario: An old Telegram review message cannot approve the new render
    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ["pubnow", "approve", "sched"])
    async def test_an_older_review_message_changes_nothing(self, kind: str) -> None:
        world = _world()
        _two_reviews(world)

        await _handle(world, _on(_tap(1, _action(kind, world)), 9))

        assert world.editorial.resumes == []
        assert world.release.ids == []
        assert world.runs.run.state is _S.AWAITING_OWNER
        assert world.messenger.answers[-1].text == ANSWER_REVIEW_REPLACED
        assert world.messenger.edits[-1].text == TEXT_REVIEW_REPLACED

    # Scenario: An old Telegram review message cannot approve the new render
    @pytest.mark.asyncio
    async def test_the_newest_review_message_still_publishes(self) -> None:
        world = _world()
        _two_reviews(world)

        await _handle(world, _on(_tap(1, _action("pubnow", world)), 20))

        assert len(world.editorial.resumes) == 1
        assert world.runs.run.state is _S.PUBLISHING

    # Scenario: An old Telegram review message cannot approve the new render
    def test_unknown_messages_and_runs_are_not_replaced(self) -> None:
        run = _run(_S.AWAITING_OWNER)
        assert is_replaced_review(None, 9) is False
        assert is_replaced_review(run, None) is False
        assert is_replaced_review(run, 9) is False
