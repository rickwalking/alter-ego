"""Typed times, the approve's CAS, exhausted reviews and the cover refusal.

Gherkin: tests/features/website_cover_review_switch_ae0594.feature
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest

from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.cover_constants import (
    COVER_REWORK_PHASE,
    REASON_COVER_REQUIRES_REVIEW,
    TEXT_REVIEW_ON_WEBSITE,
    TEXT_REVIEW_REPLACED,
)
from rag_backend.modules.autopilot.domain.cover_offer import CoverOffer
from rag_backend.modules.autopilot.domain.cover_ports import (
    CoverSwitchCommand,
    CoverSwitchStatus,
)
from rag_backend.modules.autopilot.domain.gate import GateSnapshot, ResumeStatus
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.notice_log import (
    AttemptRecord,
    NoticeLog,
    ReviewRecord,
    StoredPending,
    dump_log,
    parse_stored,
    record_review,
)
from rag_backend.modules.autopilot.schedule_constants import SCHEDULE_PENDING_PHASE
from rag_backend.modules.autopilot.webhook_constants import TEXT_APPROVE_REFUSED
from tests.unit.modules.autopilot import test_schedule_webhook_ae0370 as schedule
from tests.unit.modules.autopilot.project_inputs_fake import FakeProjectInputs
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_owner_actions import (
    _action,
    _Editorial,
    _handle,
    _Notices,
    _snapshot,
    _tap,
    _Topics,
    _world,
)

_S = AutopilotRunState
_OLD = ReviewRecord(revision=4, album_ids=(1,), keyboard_id=9)
_NEW = ReviewRecord(revision=6, album_ids=(2,), keyboard_id=20)


def _at_version(
    monkeypatch: pytest.MonkeyPatch, editorial: _Editorial, versions: list[int]
) -> None:
    """The lock version each read sees (the last one repeats)."""
    reads: list[int] = []

    async def _read_gate(project_id: str) -> GateSnapshot:
        del project_id
        reads.append(1)
        version = versions[min(len(reads), len(versions)) - 1]
        return replace(_snapshot(), lock_version=version)

    monkeypatch.setattr(editorial, "read_gate", _read_gate)


@pytest.mark.unit
class TestTypedTime:
    # Scenario: A typed publish time answers the review it was asked from
    @pytest.mark.asyncio
    async def test_a_time_typed_after_a_new_review_never_approves_it(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world = schedule._world()
        await schedule._handle(world, schedule._tap(1, world.data("other")))
        assert world.pending.item is not None
        assert world.pending.item.revision == 4
        _at_version(monkeypatch, world.editorial, [6])
        world.runs.run = replace(
            world.runs.run, notice_log=NoticeLog(reviews=(_OLD, _NEW))
        )

        await schedule._handle(world, schedule._text(2, "18:00"))

        assert world.editorial.resumes == []
        assert world.runs.run.state is _S.AWAITING_OWNER
        assert world.messenger.texts[-1].text == TEXT_REVIEW_REPLACED

    # Scenario: A typed publish time answers the review it was asked from
    @pytest.mark.asyncio
    async def test_a_refused_typed_time_sends_no_unrecorded_buttons(self) -> None:
        world = schedule._world()
        world.editorial.status = ResumeStatus.VERSION_CONFLICT
        await schedule._handle(world, schedule._tap(1, world.data("other")))

        await schedule._handle(world, schedule._text(2, "19:30"))

        told = world.messenger.texts[-1]
        assert told.text == TEXT_APPROVE_REFUSED
        assert told.keyboard is None
        assert [c.expected_version for c in world.editorial.resumes] == [4]

    # Scenario: A typed publish time answers the review it was asked from
    def test_the_pending_revision_survives_and_a_new_review_drops_it(self) -> None:
        pending = StoredPending(
            owner_chat_id="42", phase=SCHEDULE_PENDING_PHASE, revision=4
        )
        log = NoticeLog(reviews=(_OLD,), pending=pending)

        assert parse_stored(dump_log(log)).pending == pending
        assert record_review(log, _NEW).pending is None
        rework = StoredPending(owner_chat_id="42", phase="text")
        assert record_review(replace(log, pending=rework), _NEW).pending == rework


@pytest.mark.unit
class TestApproveRevision:
    # Scenario: The approve compares and sets at the tapped revision
    @pytest.mark.asyncio
    async def test_a_version_moved_after_the_guard_refuses_the_approve(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world = _world()
        _at_version(monkeypatch, world.editorial, [4, 5])
        world.editorial.status = ResumeStatus.VERSION_CONFLICT

        await _handle(world, _tap(1, _action("pubnow", world)))

        assert [c.expected_version for c in world.editorial.resumes] == [4]
        assert world.release.ids == []
        assert world.runs.run.state is _S.AWAITING_OWNER

    # Scenario: An old Telegram review message cannot approve the new render
    @pytest.mark.asyncio
    async def test_an_exhausted_current_review_points_to_the_dashboard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world = _world()
        exhausted = AttemptRecord(key="review:6", count=3)
        world.runs.run = replace(
            world.runs.run, notice_log=NoticeLog(reviews=(_OLD,), attempts=(exhausted,))
        )
        _at_version(monkeypatch, world.editorial, [6])

        await _handle(world, _tap(1, _action("pubnow", world)))

        assert world.messenger.edits[-1].text == TEXT_REVIEW_ON_WEBSITE
        assert world.runs.run.state is _S.AWAITING_OWNER
        assert world.editorial.resumes == []

    # Scenario: An old Telegram review message cannot approve the new render
    @pytest.mark.asyncio
    async def test_a_bounce_keeps_the_review_window(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world = _world()
        _at_version(monkeypatch, world.editorial, [6])
        moves: list[TransitionCommand] = []
        transition = world.runs.transition

        async def _recorded(command: TransitionCommand) -> bool:
            moves.append(command)
            return await transition(command)

        monkeypatch.setattr(world.runs, "transition", _recorded)

        await _handle(world, _tap(1, _action("pubnow", world)))

        assert [m.new for m in moves] == [_S.REWORKING]
        assert moves[0].updated_at == world.runs.run.updated_at


class _RefusingSwitch:
    async def switch(self, command: CoverSwitchCommand) -> CoverSwitchStatus:
        del command
        return CoverSwitchStatus.REQUIRES_REVIEW


class _Offer:
    async def offer(self, run: AutopilotRun) -> CoverOffer | None:
        del run
        return None

    async def chosen_cover(self, run: AutopilotRun) -> SlideCover | None:
        del run
        return SlideCover(asset_id=uuid4(), kind="ai_image", staged_path="c.webp")


@pytest.mark.unit
class TestTelegramCoverRefusal:
    # Scenario: A Telegram GrokBot cover tap on a published carousel is refused clearly
    @pytest.mark.asyncio
    async def test_the_refusal_reopens_the_review_with_its_own_reason(self) -> None:
        world = _world()
        world.runs.run = replace(
            world.runs.run, state=_S.REWORKING, rework_phase=COVER_REWORK_PHASE
        )
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
                cover_switch=_RefusingSwitch(),
            )
        )

        await runner.tick()

        assert world.runs.run.state is _S.AWAITING_OWNER
        assert world.runs.run.state_reason == REASON_COVER_REQUIRES_REVIEW
        assert world.runs.run.rework_phase is None
