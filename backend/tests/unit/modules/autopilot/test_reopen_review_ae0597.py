"""A reopened review on the autopilot side: the hook, the kept time, the worker.

Gherkin: tests/features/reopen_review_on_cover_switch_ae0597.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.modules.autopilot.application.deferred_replies import (
    DeferredOwnerMessenger,
)
from rag_backend.modules.autopilot.application.kept_slot import KeptSlotApproval
from rag_backend.modules.autopilot.application.owner_approval import (
    FinalReviewApproval,
)
from rag_backend.modules.autopilot.application.owner_replies import OwnerReplies
from rag_backend.modules.autopilot.application.review_revision_guard import (
    TappedReview,
)
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.cover_constants import (
    COVER_REWORK_PHASE,
    REASON_COVER_REVIEW_REOPENED,
)
from rag_backend.modules.autopilot.domain.cover_offer import CoverOffer
from rag_backend.modules.autopilot.domain.cover_ports import (
    CoverSwitchCommand,
    CoverSwitchStatus,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateSnapshot,
    ResumeCommand,
    ResumeResult,
    ResumeStatus,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.owner_ports import (
    CallbackAnswer,
    ForceReplyPrompt,
    MessageEdit,
    OwnerText,
    ReleaseCommand,
)
from rag_backend.modules.autopilot.domain.schedule import clears_schedule
from rag_backend.modules.autopilot.domain.state_machine import ALLOWED_TRANSITIONS
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.schedule_constants import (
    REASON_OWNER_UNSCHEDULED,
    REASON_SCHEDULE_DUE,
    REASON_SCHEDULE_WITHDRAWN,
    TEXT_KEPT_SLOT_REASON,
    TEXT_SCHEDULE_WITHDRAWN,
)
from rag_backend.modules.autopilot.webhook_constants import (
    TEXT_ALREADY,
    TEXT_APPROVE_RENDER_PENDING,
)
from tests.unit.modules.autopilot.project_inputs_fake import FakeProjectInputs
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_cover_review_hold_ae0594 import (
    _NOW,
    _PROJECT,
    _FixedClock,
    _hold,
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
_KEPT = _NOW + timedelta(hours=5)


@pytest.mark.unit
class TestReopenedHook:
    # Scenario: A reopened scheduled run keeps its time and gets a new review
    @pytest.mark.asyncio
    async def test_a_scheduled_run_goes_back_for_review_with_its_time(self) -> None:
        store = _Store(run=replace(_run(_S.SCHEDULED), scheduled_at=_KEPT))
        anchor = store.run.updated_at if store.run is not None else None

        await _hold(store).reopened(_PROJECT)

        assert store.run is not None
        assert store.run.state is _S.REWORKING
        assert store.run.state_reason == REASON_COVER_REVIEW_REOPENED
        assert store.run.updated_at == anchor
        assert store.commits == 1

    # Scenario: A cover switch reopens the review of an approved carousel
    @pytest.mark.asyncio
    async def test_a_run_waiting_for_the_owner_is_sent_a_new_review(self) -> None:
        store = _Store(run=_run(_S.AWAITING_OWNER))

        await _hold(store).reopened(_PROJECT)

        assert store.run is not None
        assert store.run.state is _S.REWORKING
        assert store.run.state_reason == REASON_COVER_REVIEW_REOPENED

    # Scenario: A cover switch reopens the review of an approved carousel
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "state", [_S.REWORKING, _S.PUBLISHING, _S.PUBLISHED, _S.EXPIRED]
    )
    async def test_other_runs_are_left_alone(self, state: AutopilotRunState) -> None:
        store = _Store(run=_run(state))

        await _hold(store).reopened(_PROJECT)

        assert store.run is not None
        assert store.run.state is state
        assert store.commits == 0

    # Scenario: A cover switch reopens the review of an approved carousel
    @pytest.mark.asyncio
    async def test_no_run_is_nothing_to_do(self) -> None:
        store = _Store(run=None)

        await _hold(store).reopened(_PROJECT)

        assert store.commits == 0

    # Scenario: A reopened scheduled run keeps its time and gets a new review
    def test_the_reopen_keeps_the_time_and_is_allowed(self) -> None:
        run_id = uuid4()

        def _leaving(reason: str) -> TransitionCommand:
            return TransitionCommand(
                run_id=run_id, expected=_S.SCHEDULED, new=_S.REWORKING, reason=reason
            )

        assert (_S.SCHEDULED, _S.REWORKING) in ALLOWED_TRANSITIONS
        assert not clears_schedule(_leaving(REASON_COVER_REVIEW_REOPENED))
        assert not clears_schedule(_leaving(REASON_SCHEDULE_DUE))
        assert clears_schedule(_leaving(REASON_OWNER_UNSCHEDULED))


@dataclass
class _Messenger:
    """Records what the owner is shown."""

    answers: list[str] = field(default_factory=list)
    edits: list[str] = field(default_factory=list)

    async def answer(self, command: CallbackAnswer) -> None:
        self.answers.append(command.text)

    async def edit(self, command: MessageEdit) -> None:
        self.edits.append(command.text)

    async def tell(self, command: OwnerText) -> None:
        del command

    async def ask(self, command: ForceReplyPrompt) -> None:
        del command


@dataclass
class _Editorial:
    status: ResumeStatus = ResumeStatus.APPLIED
    resumes: list[ResumeCommand] = field(default_factory=list)

    async def read_gate(self, project_id: str) -> GateSnapshot:
        del project_id
        return _snapshot()

    async def resume(self, command: ResumeCommand) -> ResumeResult:
        self.resumes.append(command)
        return ResumeResult(status=self.status)


class _NoRelease:
    async def release(self, command: ReleaseCommand) -> bool:
        raise AssertionError(command)


@dataclass
class _Deps:
    runs: _Store
    approval: FinalReviewApproval
    clock: _FixedClock


@dataclass
class _Kept:
    """The kept-slot approve over in-memory stores, and what it showed."""

    store: _Store
    editorial: _Editorial
    messenger: _Messenger
    deferred: DeferredOwnerMessenger

    @property
    def approval(self) -> KeptSlotApproval:
        approval = FinalReviewApproval(
            editorial=self.editorial, release_port=_NoRelease()
        )
        deps = _Deps(runs=self.store, approval=approval, clock=_FixedClock())
        return KeptSlotApproval(deps, OwnerReplies(self.deferred))

    async def tap(self, run: AutopilotRun | None) -> None:
        await self.approval.approve(_tap(), TappedReview(run=run, revision=6))
        await self.deferred.deliver()


def _kept(at: datetime, status: ResumeStatus = ResumeStatus.APPLIED) -> _Kept:
    messenger = _Messenger()
    return _Kept(
        store=_Store(run=replace(_run(_S.AWAITING_OWNER), scheduled_at=at)),
        editorial=_Editorial(status=status),
        messenger=messenger,
        deferred=DeferredOwnerMessenger(messenger),
    )


def _tap() -> WebhookUpdate:
    return WebhookUpdate(
        update_id=1,
        kind="callback_query",
        actor_id="7",
        chat_id="7",
        callback_id="cb",
        message_id=20,
    )


@pytest.mark.unit
class TestKeptSlot:
    # Scenario: Approving the new review keeps the scheduled time
    @pytest.mark.asyncio
    async def test_the_approve_schedules_the_run_again_at_its_time(self) -> None:
        kept = _kept(_KEPT)

        await kept.tap(kept.store.run)

        assert [r.expected_version for r in kept.editorial.resumes] == [6]
        assert kept.store.run is not None
        assert kept.store.run.state is _S.SCHEDULED
        assert TEXT_KEPT_SLOT_REASON in kept.messenger.edits[-1]

    # Scenario: A slot that passes while the review waits does not publish
    @pytest.mark.asyncio
    async def test_a_passed_time_expires_without_approving(self) -> None:
        kept = _kept(_NOW - timedelta(minutes=1))

        await kept.tap(kept.store.run)

        assert kept.editorial.resumes == []
        assert kept.store.run is not None
        assert kept.store.run.state is _S.EXPIRED
        assert kept.store.run.state_reason == REASON_SCHEDULE_WITHDRAWN
        assert kept.messenger.edits == [TEXT_SCHEDULE_WITHDRAWN]

    # Scenario: Approving the new review keeps the scheduled time
    @pytest.mark.asyncio
    async def test_a_refused_approve_moves_nothing(self) -> None:
        kept = _kept(_KEPT, ResumeStatus.RENDER_PENDING)

        await kept.tap(kept.store.run)

        assert kept.store.run is not None
        assert kept.store.run.state is _S.AWAITING_OWNER
        assert kept.store.run.scheduled_at == _KEPT
        assert kept.messenger.edits == [TEXT_APPROVE_RENDER_PENDING]

    # Scenario: Approving the new review keeps the scheduled time
    @pytest.mark.asyncio
    async def test_a_lost_move_answers_already(self) -> None:
        kept = _kept(_KEPT)
        kept.store.lose = True

        await kept.tap(kept.store.run)

        assert kept.store.run is not None
        assert kept.store.run.state is _S.AWAITING_OWNER
        assert kept.messenger.edits == [TEXT_ALREADY]

    # Scenario: A slot that passes while the review waits does not publish
    @pytest.mark.asyncio
    async def test_a_lost_expiry_answers_already(self) -> None:
        kept = _kept(_NOW - timedelta(minutes=1))
        kept.store.lose = True

        await kept.tap(kept.store.run)

        assert kept.messenger.edits == [TEXT_ALREADY]

    # Scenario: Approving the new review keeps the scheduled time
    @pytest.mark.asyncio
    async def test_a_run_without_a_time_answers_already(self) -> None:
        kept = _kept(_KEPT)

        await kept.tap(None)

        assert kept.editorial.resumes == []
        assert kept.messenger.edits == [TEXT_ALREADY]


class _Switch:
    def __init__(self) -> None:
        self.commands: list[CoverSwitchCommand] = []

    async def switch(self, command: CoverSwitchCommand) -> CoverSwitchStatus:
        self.commands.append(command)
        return CoverSwitchStatus.SWITCHED


class _Offer:
    async def offer(self, run: AutopilotRun) -> CoverOffer | None:
        del run
        return None

    async def chosen_cover(self, run: AutopilotRun) -> SlideCover | None:
        del run
        return SlideCover(asset_id=uuid4(), kind="ai_image", staged_path="c.webp")


@pytest.mark.unit
class TestGrokCoverOnAnApprovedCarousel:
    # Scenario: A cover switch reopens the review of an approved carousel
    @pytest.mark.asyncio
    async def test_the_grokbot_cover_runs_on_an_approved_carousel(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world = _world()
        world.runs.run = replace(
            world.runs.run, state=_S.REWORKING, rework_phase=COVER_REWORK_PHASE
        )
        approved = replace(_snapshot(), phase_status="approved")

        async def _read_gate(project_id: str) -> GateSnapshot:
            del project_id
            return approved

        monkeypatch.setattr(world.editorial, "read_gate", _read_gate)
        switch = _Switch()
        runner = AutopilotRunner(
            RunnerDependencies(
                runs=world.runs,
                topics=_Topics(),
                editorial=world.editorial,
                notices=_Notices(),
                recovery=_Recovery(runs=world.runs),
                owner_user_id="owner",
                inputs=FakeProjectInputs(),
                covers=_Offer(),
                cover_switch=switch,
            )
        )

        await runner.tick()

        assert len(switch.commands) == 1
        assert switch.commands[0].expected_version == approved.lock_version
