"""Telegram approve, publish and schedule are bound to the tapped revision.

Gherkin: tests/features/website_cover_review_switch_ae0594.feature
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from rag_backend.modules.autopilot.cover_constants import (
    ANSWER_REVIEW_REPLACED,
    REASON_REVIEW_OUTDATED,
    TEXT_REVIEW_REPLACED,
    TEXT_REVIEW_RESENDING,
)
from rag_backend.modules.autopilot.domain.gate import GateSnapshot
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.notice_log import (
    NoticeLog,
    ReminderRecord,
    ReviewRecord,
    dump_log,
    parse_stored,
    record_reminder,
)
from rag_backend.modules.autopilot.domain.review_revision import tapped_revision
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from tests.unit.modules.autopilot import test_schedule_webhook_ae0370 as schedule
from tests.unit.modules.autopilot.test_owner_actions import (
    _action,
    _Editorial,
    _handle,
    _snapshot,
    _tap,
    _World,
    _world,
)

_S = AutopilotRunState
_OLD = ReviewRecord(revision=4, album_ids=(1,), keyboard_id=9)
_NEW = ReviewRecord(revision=6, album_ids=(2,), keyboard_id=20)


def _at_version(
    monkeypatch: pytest.MonkeyPatch, editorial: _Editorial, version: int
) -> None:
    """The carousel's current lock version, as the approve reads it."""

    async def _read_gate(project_id: str) -> GateSnapshot:
        del project_id
        return replace(_snapshot(), lock_version=version)

    monkeypatch.setattr(editorial, "read_gate", _read_gate)


def _logged(world: _World, log: NoticeLog) -> None:
    world.runs.run = replace(world.runs.run, notice_log=log)


def _on(update: WebhookUpdate, message_id: int) -> WebhookUpdate:
    return replace(update, message_id=message_id)


def _assert_refused(world: _World, text: str = TEXT_REVIEW_REPLACED) -> None:
    assert world.editorial.resumes == []
    assert world.release.ids == []
    assert world.messenger.answers[-1].text == ANSWER_REVIEW_REPLACED
    assert world.messenger.edits[-1].text == text


@pytest.mark.unit
class TestOutdatedReview:
    # Scenario: An old Telegram review message cannot approve the new render
    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ["pubnow", "approve", "sched"])
    async def test_old_review_before_the_new_one_is_sent_is_refused(
        self, monkeypatch: pytest.MonkeyPatch, kind: str
    ) -> None:
        world = _world()
        _at_version(monkeypatch, world.editorial, 6)

        await _handle(world, _on(_tap(1, _action(kind, world)), 9))

        _assert_refused(world, TEXT_REVIEW_RESENDING)
        assert world.runs.run.state is _S.REWORKING
        assert world.runs.run.state_reason == REASON_REVIEW_OUTDATED

    # Scenario: An old Telegram review message cannot approve the new render
    @pytest.mark.asyncio
    async def test_old_review_after_the_new_one_was_sent_is_refused(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world = _world()
        _logged(world, NoticeLog(reviews=(_OLD, _NEW)))
        _at_version(monkeypatch, world.editorial, 6)

        await _handle(world, _on(_tap(1, _action("pubnow", world)), 9))

        _assert_refused(world)
        assert world.runs.run.state is _S.AWAITING_OWNER

    # Scenario: An old Telegram reminder cannot approve the new render
    @pytest.mark.asyncio
    async def test_old_reminder_is_refused(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world = _world()
        old_nudge = ReminderRecord(revision=4, message_id=30)
        _logged(world, NoticeLog(reviews=(_OLD, _NEW), reminder_messages=(old_nudge,)))
        _at_version(monkeypatch, world.editorial, 6)

        await _handle(world, _on(_tap(1, _action("pubnow", world)), 30))

        _assert_refused(world)

    # Scenario: An unknown Telegram message cannot approve anything
    @pytest.mark.asyncio
    async def test_unknown_message_is_refused(self) -> None:
        world = _world()

        await _handle(world, _on(_tap(1, _action("pubnow", world)), 77))

        _assert_refused(world)

    # Scenario: The current Telegram review or reminder still publishes and schedules
    @pytest.mark.asyncio
    async def test_current_reminder_publishes_at_its_revision(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world = _world()
        nudge = ReminderRecord(revision=6, message_id=31)
        _logged(world, NoticeLog(reviews=(_OLD, _NEW), reminder_messages=(nudge,)))
        _at_version(monkeypatch, world.editorial, 6)

        await _handle(world, _on(_tap(1, _action("pubnow", world)), 31))

        assert [c.expected_version for c in world.editorial.resumes] == [6]
        assert world.runs.run.state is _S.PUBLISHING

    # Scenario: The current Telegram review or reminder still publishes and schedules
    @pytest.mark.asyncio
    async def test_approve_after_a_rework_from_the_newest_review(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world = _world()
        _logged(world, NoticeLog(reviews=(_OLD, _NEW)))
        _at_version(monkeypatch, world.editorial, 6)

        await _handle(world, _on(_tap(1, _action("approve", world)), 20))
        await _handle(world, _on(_tap(2, _action("pubnow", world)), 20))

        assert [c.expected_version for c in world.editorial.resumes] == [6]
        assert world.runs.run.state is _S.PUBLISHING
        assert world.release.ids != []


@pytest.mark.unit
class TestScheduleRevision:
    # Scenario: The current Telegram review or reminder still publishes and schedules
    @pytest.mark.asyncio
    async def test_slot_on_the_current_review_schedules_at_its_revision(self) -> None:
        world = schedule._world()

        await schedule._schedule_slot(world, schedule._local(15, 18))

        assert world.runs.run.state is _S.SCHEDULED
        assert [c.expected_version for c in world.editorial.resumes] == [4]

    # Scenario: An old Telegram review message cannot approve the new render
    @pytest.mark.asyncio
    async def test_slot_on_an_old_review_is_refused(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world = schedule._world()
        _at_version(monkeypatch, world.editorial, 6)

        await schedule._schedule_slot(world, schedule._local(15, 18))

        assert world.runs.run.state is _S.REWORKING
        assert world.editorial.resumes == []

    # Scenario: An old Telegram review message cannot approve the new render
    @pytest.mark.asyncio
    async def test_typed_time_for_an_outdated_review_is_refused(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world = schedule._world()
        await schedule._handle(world, schedule._tap(1, world.data("other")))
        _at_version(monkeypatch, world.editorial, 6)

        await schedule._handle(world, schedule._text(2, "19:30"))

        assert world.runs.run.state is _S.REWORKING
        assert world.editorial.resumes == []
        assert world.messenger.texts[-1].text == TEXT_REVIEW_RESENDING


@pytest.mark.unit
class TestRevisionLedger:
    # Scenario: An old Telegram reminder cannot approve the new render
    def test_reminder_messages_survive_the_ledger(self) -> None:
        log = record_reminder(NoticeLog(reviews=(_OLD,)), 4, 30)
        log = record_reminder(log, 4, 32)

        parsed = parse_stored(dump_log(log))

        assert parsed.reminder_messages == (
            ReminderRecord(revision=4, message_id=30),
            ReminderRecord(revision=4, message_id=32),
        )
        assert parsed.reminders == (4,)
        assert (
            parse_stored({"reminder_ids": {"x": [1], "5": "bad"}}).reminder_messages
            == ()
        )

    # Scenario: An unknown Telegram message cannot approve anything
    def test_tapped_revision(self) -> None:
        run = replace(_world().runs.run, notice_log=NoticeLog(reviews=(_OLD, _NEW)))

        assert tapped_revision(run, 9) == 4
        assert tapped_revision(run, 20) == 6
        assert tapped_revision(run, 77) is None
        assert tapped_revision(run, None) is None
        assert tapped_revision(None, 9) is None
