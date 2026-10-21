"""Telegram publish-now and scheduling flows.

Gherkin: tests/features/autopilot_scheduled_publish.feature
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest

from rag_backend.modules.autopilot.application.owner_actions import (
    OwnerActionDeps,
    OwnerActionService,
)
from rag_backend.modules.autopilot.domain.gate import ResumeStatus
from rag_backend.modules.autopilot.domain.messages import review_keyboard
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.ports import CarouselPublishSnapshot
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.schedule import (
    clears_schedule,
    epoch_of,
)
from rag_backend.modules.autopilot.domain.schedule_keyboards import (
    publish_choice_keyboard,
    scheduled_keyboard,
)
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.recovery_constants import REASON_APPROVE_REFUSED
from rag_backend.modules.autopilot.schedule_constants import (
    ANSWER_SCHEDULED,
    REASON_OWNER_SCHEDULED,
    SCHEDULE_PENDING_PHASE,
    TEXT_ASK_TIME,
    TEXT_CHOOSE_DAY,
    TEXT_PUBLISH_CHOICE,
    TEXT_TIME_FORMAT,
    TEXT_TIME_PAST,
    TEXT_TIME_TOO_FAR,
)
from rag_backend.modules.autopilot.webhook_constants import (
    ANSWER_ALREADY,
    TEXT_ALREADY,
    TEXT_APPROVE_REFUSED,
    TEXT_APPROVED,
    TEXT_REWORKING,
)
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_owner_actions import (
    _OWNER,
    _PROJECT,
    _Claims,
    _Editorial,
    _Messenger,
    _Pending,
    _Release,
    _tap,
    _text,
)

_SP = ZoneInfo("America/Sao_Paulo")
_S = AutopilotRunState
_NOW = datetime(2026, 10, 15, 10, 0, tzinfo=_SP).astimezone(UTC)


def _local(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=_SP).astimezone(UTC)


@dataclass
class _Clock:
    at: datetime = _NOW

    def now(self) -> datetime:
        return self.at


@dataclass
class _Runs:
    """CAS fake that stores and clears ``scheduled_at`` like the SQL adapter."""

    run: AutopilotRun
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    commands: list[TransitionCommand] = field(default_factory=list)

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        await asyncio.sleep(0)
        return self.run if self.run.run_id == run_id else None

    async def transition(self, command: TransitionCommand) -> bool:
        await asyncio.sleep(0)
        async with self.lock:
            if self.run.state is not command.expected:
                return False
            self.commands.append(command)
            scheduled_at = self.run.scheduled_at
            if command.new is _S.SCHEDULED:
                scheduled_at = command.scheduled_at
            elif clears_schedule(command):
                scheduled_at = None
            self.run = replace(
                self.run,
                state=command.new,
                state_reason=command.reason,
                scheduled_at=scheduled_at,
            )
            return True

    async def list_by_state(self, query: RunListQuery) -> list[AutopilotRun]:
        return [self.run] if self.run.state is query.state else []


@dataclass
class _Carousels:
    workflow_status: str = "draft"

    async def load(self, project_id: str) -> CarouselPublishSnapshot | None:
        del project_id
        return CarouselPublishSnapshot(
            workflow_status=self.workflow_status,
            status="completed",
            is_public=False,
            caption="c",
            image_urls=("u",),
            base_url_configured=True,
        )


@dataclass
class _World:
    runs: _Runs
    pending: _Pending
    editorial: _Editorial
    release: _Release
    messenger: _Messenger
    carousels: _Carousels
    clock: _Clock
    service: OwnerActionService

    @property
    def run_id(self) -> UUID:
        return self.runs.run.run_id

    def data(self, kind: str) -> str:
        return f"ap:{kind}:{self.run_id}"

    def slot(self, at: datetime) -> str:
        return f"ap:at:{epoch_of(at)}:{self.run_id}"


def _world(
    default_publish: str = "now", state: AutopilotRunState = _S.AWAITING_OWNER
) -> _World:
    run = AutopilotRun(
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
    runs = _Runs(run=run)
    parts = {
        "pending": _Pending(),
        "editorial": _Editorial(),
        "release": _Release(),
        "messenger": _Messenger(),
        "carousels": _Carousels(),
        "clock": _Clock(),
    }
    service = OwnerActionService(
        OwnerActionDeps(
            runs=runs,
            updates=_Claims(),
            pending=parts["pending"],
            editorial=parts["editorial"],
            release=parts["release"],
            messenger=parts["messenger"],
            recovery=_Recovery(runs=runs),
            clock=parts["clock"],
            owner_chat_id=_OWNER,
            carousels=parts["carousels"],
            default_publish=default_publish,
        )
    )
    return _World(runs=runs, service=service, **parts)


async def _handle(world: _World, update: WebhookUpdate) -> None:
    await world.service.handle(update)
    await world.service.deliver()


async def _schedule_slot(world: _World, at: datetime, update_id: int = 1) -> None:
    await _handle(world, _tap(update_id, world.slot(at)))


# Scenario: Approve offers publish now or schedule
@pytest.mark.asyncio
async def test_approve_offers_publish_now_or_schedule() -> None:
    world = _world()
    await _handle(world, _tap(1, world.data("approve")))
    edit = world.messenger.edits[-1]
    assert edit.text == TEXT_PUBLISH_CHOICE
    assert edit.keyboard == publish_choice_keyboard(world.run_id)
    assert world.runs.run.state is _S.AWAITING_OWNER
    assert world.editorial.resumes == []
    assert world.release.ids == []


# Scenario: Publish now keeps today's approve behaviour
@pytest.mark.asyncio
async def test_publish_now_approves_and_releases() -> None:
    world = _world()
    await _handle(world, _tap(1, world.data("approve")))
    await _handle(world, _tap(2, world.data("pubnow")))
    assert len(world.editorial.resumes) == 1
    assert world.release.ids == [_PROJECT]
    assert world.runs.run.state is _S.PUBLISHING
    assert world.messenger.edits[-1].text == TEXT_APPROVED


# Scenario: Agendar opens the day step of the picker (AE-0404)
@pytest.mark.asyncio
async def test_schedule_menu_lists_days() -> None:
    world = _world()
    await _handle(world, _tap(1, world.data("sched")))
    edit = world.messenger.edits[-1]
    assert edit.text == TEXT_CHOOSE_DAY
    assert edit.keyboard is not None
    labels = [button.text for row in edit.keyboard.rows for button in row]
    assert labels[0] == "Qui 15/10"
    assert len(labels) == 7
    assert world.runs.run.state is _S.AWAITING_OWNER


# Scenario: Choosing a slot schedules the run
@pytest.mark.asyncio
async def test_slot_schedules_without_release() -> None:
    world = _world()
    await _schedule_slot(world, _local(15, 18))
    run = world.runs.run
    assert run.state is _S.SCHEDULED
    assert run.state_reason == REASON_OWNER_SCHEDULED
    assert run.scheduled_at == _local(15, 18)
    assert len(world.editorial.resumes) == 1
    assert world.release.ids == []
    edit = world.messenger.edits[-1]
    assert edit.text == "\U0001f5d3 Agendado para Qui 15/10 18:00 (horário padrão)"
    assert edit.keyboard == scheduled_keyboard(world.run_id)
    assert world.messenger.answers[-1].text == ANSWER_SCHEDULED


# Scenario: A double tap schedules once
@pytest.mark.asyncio
async def test_double_tap_schedules_once() -> None:
    world = _world()
    await asyncio.gather(
        _schedule_slot(world, _local(15, 18), 1),
        _schedule_slot(world, _local(15, 18), 2),
    )
    assert len(world.editorial.resumes) == 1
    assert world.runs.run.state is _S.SCHEDULED
    assert [a.text for a in world.messenger.answers].count(ANSWER_ALREADY) == 1


@pytest.mark.asyncio
async def test_stale_slot_offers_fresh_days() -> None:
    world = _world()
    await _schedule_slot(world, _local(15, 9))
    assert world.runs.run.state is _S.AWAITING_OWNER
    assert world.messenger.answers[-1].text == TEXT_TIME_PAST
    assert world.messenger.edits[-1].text == TEXT_CHOOSE_DAY
    assert world.editorial.resumes == []


# Scenario: A refused editorial approve keeps the review open
@pytest.mark.asyncio
async def test_refused_schedule_reopens_the_review() -> None:
    world = _world()
    world.editorial.status = ResumeStatus.VERSION_CONFLICT
    await _schedule_slot(world, _local(15, 18))
    assert world.runs.run.state is _S.AWAITING_OWNER
    assert world.runs.run.state_reason == REASON_APPROVE_REFUSED
    assert world.runs.run.scheduled_at is None
    assert world.messenger.edits[-1].text == TEXT_APPROVE_REFUSED
    assert world.messenger.edits[-1].keyboard == review_keyboard(world.run_id)


# Scenario: Outro horário asks for a time with ForceReply
@pytest.mark.asyncio
async def test_other_time_asks_with_force_reply() -> None:
    world = _world()
    await _handle(world, _tap(1, world.data("other")))
    assert world.messenger.asks[-1].text == TEXT_ASK_TIME
    assert world.pending.item is not None
    assert world.pending.item.phase == SCHEDULE_PENDING_PHASE


# Scenario Outline: The owner types a valid time
@pytest.mark.asyncio
async def test_typed_time_schedules_with_buttons_in_a_new_message() -> None:
    world = _world()
    await _handle(world, _tap(1, world.data("other")))
    await _handle(world, _text(2, "19:30"))
    assert world.runs.run.state is _S.SCHEDULED
    assert world.runs.run.scheduled_at == _local(15, 19, 30)
    told = world.messenger.texts[-1]
    assert told.text == "\U0001f5d3 Agendado para Qui 15/10 19:30"
    assert told.keyboard == scheduled_keyboard(world.run_id)
    assert world.pending.item is None


# Scenario Outline: The owner types an invalid time
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "reply"),
    [
        ("amanhã", TEXT_TIME_FORMAT),
        ("15/10 09:00", TEXT_TIME_PAST),
        ("20/12 10:00", TEXT_TIME_TOO_FAR),
    ],
)
async def test_invalid_typed_time_asks_again(text: str, reply: str) -> None:
    world = _world()
    await _handle(world, _tap(1, world.data("other")))
    await _handle(world, _text(2, text))
    assert world.runs.run.state is _S.AWAITING_OWNER
    assert world.messenger.texts[-1].text == reply
    assert world.messenger.asks[-1].text == TEXT_ASK_TIME
    assert len(world.messenger.asks) == 2
    assert world.pending.item is not None
    await _handle(world, _text(3, "21:00"))
    assert world.runs.run.state is _S.SCHEDULED


@pytest.mark.asyncio
async def test_typed_time_after_the_run_moved_is_already_handled() -> None:
    world = _world()
    await _handle(world, _tap(1, world.data("other")))
    world.runs.run = replace(world.runs.run, state=_S.REJECTED)
    await _handle(world, _text(2, "19:30"))
    assert world.runs.run.state is _S.REJECTED
    assert world.messenger.texts[-1].text == TEXT_ALREADY


@pytest.mark.asyncio
async def test_rework_text_still_reworks() -> None:
    world = _world()
    await _handle(world, _tap(1, f"ap:rw:design:{world.run_id}"))
    await _handle(world, _text(2, "darker"))
    assert world.runs.run.state is _S.REWORKING
    assert world.messenger.texts[-1].text == TEXT_REWORKING.format(phase="design")
