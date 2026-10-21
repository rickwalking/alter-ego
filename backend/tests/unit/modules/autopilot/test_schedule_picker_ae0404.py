"""The Telegram day/time picker over the owner-action service.

Gherkin: tests/features/telegram_schedule_picker_ae0404.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from rag_backend.modules.autopilot.application.owner_actions import (
    OwnerActionDeps,
    OwnerActionService,
)
from rag_backend.modules.autopilot.domain.callback_parse import parse_callback
from rag_backend.modules.autopilot.domain.messages import (
    InlineKeyboard,
    review_keyboard,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.recommend import ScheduleSignals
from rag_backend.modules.autopilot.domain.schedule import epoch_of
from rag_backend.modules.autopilot.domain.schedule_keyboards import (
    scheduled_keyboard,
)
from rag_backend.modules.autopilot.schedule_constants import (
    ANSWER_SCHEDULED,
    REASON_OWNER_RESCHEDULED,
    TEXT_CHOOSE_DAY,
    TEXT_DAY_OUT_OF_RANGE,
    TEXT_TIME_PAST,
    TEXT_TIME_TOO_FAR,
)
from rag_backend.modules.autopilot.webhook_constants import (
    ANSWER_ALREADY,
    TEXT_ALREADY,
    TEXT_APPROVED,
)
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_owner_actions import (
    _OWNER,
    _PROJECT,
    _Claims,
    _tap,
    _text,
)
from tests.unit.modules.autopilot.test_schedule_webhook_ae0370 import (
    _handle,
    _Runs,
    _World,
    _world,
)

_SP = ZoneInfo("America/Sao_Paulo")
_S = AutopilotRunState
_THESIS = "A IA escreve código; decidir o que construir continua sendo do dev."


def _local(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=_SP).astimezone(UTC)


@dataclass
class _Signals:
    signals: ScheduleSignals = field(default_factory=ScheduleSignals)
    loads: int = 0

    async def load(self) -> ScheduleSignals:
        self.loads += 1
        return self.signals


@dataclass
class _RacingRuns(_Runs):
    """The due tick wins every compare-and-set."""

    async def transition(self, command: TransitionCommand) -> bool:
        del command
        self.run = replace(self.run, state=_S.PUBLISHING)
        return False


def _picker_world(
    default_publish: str = "now", signals: _Signals | None = None
) -> tuple[_World, _Signals]:
    """The scheduling world on Friday 16/10 10:00, with a signals source wired."""
    world = _world(default_publish=default_publish)
    world.clock.at = _local(16, 10)
    return world, _wire(world, signals or _Signals(), default_publish)


def _wire(world: _World, source: _Signals, default_publish: str = "now") -> _Signals:
    world.service = OwnerActionService(
        OwnerActionDeps(
            runs=world.runs,
            updates=_Claims(),
            pending=world.pending,
            editorial=world.editorial,
            release=world.release,
            messenger=world.messenger,
            recovery=_Recovery(runs=world.runs),
            clock=world.clock,
            owner_chat_id=_OWNER,
            carousels=world.carousels,
            default_publish=default_publish,
            schedule_signals=source,
        )
    )
    return source


def _day(world: _World, day: int) -> str:
    return f"ap:d:202610{day:02d}:{world.run_id}"


def _slot(world: _World, at: datetime) -> str:
    return f"ap:at:{epoch_of(at)}:{world.run_id}"


def _labels(keyboard: InlineKeyboard | None) -> list[list[str]]:
    assert keyboard is not None
    return [[button.text for button in row] for row in keyboard.rows]


def _scheduled(world: _World, at: datetime) -> None:
    world.runs.run = replace(world.runs.run, state=_S.SCHEDULED, scheduled_at=at)


# Scenario: An auto-scheduled message offers to change the day and time
@pytest.mark.asyncio
async def test_auto_scheduled_message_offers_mudar_dia_horario() -> None:
    world, signals = _picker_world(default_publish="next_slot")
    await _handle(world, _tap(1, world.data("approve")))
    assert world.runs.run.state is _S.SCHEDULED
    assert world.runs.run.scheduled_at == _local(16, 12)
    edit = world.messenger.edits[-1]
    assert edit.text == "\U0001f5d3 Agendado para Sex 16/10 12:00 (horário padrão)"
    assert edit.keyboard == scheduled_keyboard(world.run_id)
    assert _labels(edit.keyboard) == [
        ["\U0001f680 Publicar agora", "\U0001f5d3 Mudar dia/horário"],
        ["❌ Cancelar agendamento"],
    ]
    assert edit.keyboard.rows[0][1].callback_data == f"ap:sched:{world.run_id}"
    assert signals.loads == 1


@pytest.mark.asyncio
async def test_auto_slot_follows_the_audience_peak() -> None:
    """Hour 23 UTC is 20:00 in São Paulo."""
    audience = dict.fromkeys(range(24), 10)
    audience[23] = 90
    source = _Signals(signals=ScheduleSignals(audience=audience))
    world, _ = _picker_world(default_publish="next_slot", signals=source)
    await _handle(world, _tap(1, world.data("approve")))
    assert world.runs.run.scheduled_at == _local(16, 20)
    assert world.messenger.edits[-1].text.endswith("(⭐ seus seguidores mais online)")


# Scenario: The review keyboard opens the same picker
@pytest.mark.asyncio
async def test_review_keyboard_agendar_opens_the_day_step() -> None:
    world, _ = _picker_world()
    keyboard = review_keyboard(world.run_id)
    assert keyboard.rows[1][0].text == "\U0001f5d3 Agendar"
    await _handle(world, _tap(1, keyboard.rows[1][0].callback_data))
    assert world.messenger.edits[-1].text == TEXT_CHOOSE_DAY
    assert world.messenger.answers[-1].text == TEXT_CHOOSE_DAY


# Scenario: The day keyboard lists the next 7 days and stars the best ones
@pytest.mark.asyncio
async def test_day_keyboard_lists_seven_days_three_per_row() -> None:
    world, _ = _picker_world()
    world.runs.run = replace(world.runs.run, pov_thesis=_THESIS)
    await _handle(world, _tap(1, world.data("sched")))
    keyboard = world.messenger.edits[-1].keyboard
    assert _labels(keyboard) == [
        ["Sex 16/10", "Sáb 17/10", "Dom 18/10"],
        ["Seg 19/10", "Ter 20/10 ⭐", "Qua 21/10"],
        ["Qui 22/10 ⭐"],
    ]
    assert keyboard is not None
    assert keyboard.rows[1][1].callback_data == _day(world, 20)


# Scenario: The time keyboard shows the top 4 times, a custom time and back
@pytest.mark.asyncio
async def test_time_keyboard_shows_top_four_times_with_reasons() -> None:
    world, _ = _picker_world()
    world.runs.run = replace(world.runs.run, pov_thesis=_THESIS)
    await _handle(world, _tap(1, _day(world, 20)))
    edit = world.messenger.edits[-1]
    assert edit.text.splitlines() == [
        "Escolha o horário para Ter 20/10 (horário de Brasília):",
        "12:00 — padrão do plano POV",
        "18:00 — horário padrão",
        "21:00 — horário padrão",
        "11:00 — horário alternativo",
    ]
    assert _labels(edit.keyboard) == [
        ["12:00 ⭐", "18:00"],
        ["21:00", "11:00"],
        ["✏️ Outro horário", "← Dias"],
    ]
    assert world.messenger.answers[-1].text == "Ter 20/10"


@pytest.mark.asyncio
async def test_back_to_days_shows_the_day_step() -> None:
    world, _ = _picker_world()
    await _handle(world, _tap(1, _day(world, 20)))
    await _handle(world, _tap(2, world.data("days")))
    assert world.messenger.edits[-1].text == TEXT_CHOOSE_DAY


# Scenario: A day outside the 7-day window is refused
@pytest.mark.asyncio
@pytest.mark.parametrize("day", [15, 23, 30])
async def test_day_outside_the_window_shows_the_days_again(day: int) -> None:
    world, _ = _picker_world()
    await _handle(world, _tap(1, _day(world, day)))
    assert world.messenger.answers[-1].text == TEXT_DAY_OUT_OF_RANGE
    assert world.messenger.edits[-1].text == TEXT_CHOOSE_DAY
    assert world.runs.run.state is _S.AWAITING_OWNER


# Scenario: Confirming a slot schedules an awaiting run
@pytest.mark.asyncio
async def test_slot_schedules_an_awaiting_run_with_its_reason() -> None:
    world, _ = _picker_world()
    await _handle(world, _tap(1, _day(world, 20)))
    await _handle(world, _tap(2, _slot(world, _local(20, 18))))
    assert world.runs.run.state is _S.SCHEDULED
    assert world.runs.run.scheduled_at == _local(20, 18)
    edit = world.messenger.edits[-1]
    assert edit.text == "\U0001f5d3 Agendado para Ter 20/10 18:00 (horário padrão)"
    assert edit.keyboard == scheduled_keyboard(world.run_id)
    assert len(world.editorial.resumes) == 1
    assert world.release.ids == []


# Scenario: Confirming a slot reschedules a scheduled run
@pytest.mark.asyncio
async def test_slot_reschedules_a_scheduled_run_idempotently() -> None:
    """Final review was approved when the run was first scheduled, not again."""
    world, _ = _picker_world()
    _scheduled(world, _local(20, 12))
    await _handle(world, _tap(1, world.data("sched")))
    assert world.messenger.edits[-1].text == TEXT_CHOOSE_DAY
    await _handle(world, _tap(2, _slot(world, _local(21, 18))))
    assert world.runs.run.state is _S.SCHEDULED
    assert world.runs.run.state_reason == REASON_OWNER_RESCHEDULED
    assert world.runs.run.scheduled_at == _local(21, 18)
    edit = world.messenger.edits[-1]
    assert edit.text == "\U0001f5d3 Agendado para Qua 21/10 18:00 (horário padrão)"
    assert edit.keyboard == scheduled_keyboard(world.run_id)
    assert world.messenger.answers[-1].text == ANSWER_SCHEDULED
    await _handle(world, _tap(3, _slot(world, _local(21, 18))))
    assert world.runs.run.scheduled_at == _local(21, 18)
    assert world.editorial.resumes == []


@pytest.mark.asyncio
async def test_reschedule_after_the_due_tick_is_already_handled() -> None:
    world, _ = _picker_world()
    _scheduled(world, _local(20, 12))
    world.runs = _RacingRuns(run=world.runs.run)
    _wire(world, _Signals())
    await _handle(world, _tap(1, _slot(world, _local(21, 18))))
    assert world.messenger.answers[-1].text == ANSWER_ALREADY
    assert world.messenger.edits[-1].text == TEXT_ALREADY


# Scenario: The typed "Outro horário" reschedules a scheduled run
@pytest.mark.asyncio
async def test_typed_time_reschedules_a_scheduled_run() -> None:
    world, _ = _picker_world()
    _scheduled(world, _local(20, 12))
    await _handle(world, _tap(1, world.data("other")))
    await _handle(world, _text(2, "21/10 19:30"))
    assert world.runs.run.state is _S.SCHEDULED
    assert world.runs.run.scheduled_at == _local(21, 19, 30)
    told = world.messenger.texts[-1]
    assert told.text == "\U0001f5d3 Agendado para Qua 21/10 19:30"
    assert told.keyboard == scheduled_keyboard(world.run_id)


# Scenario Outline: A past slot or one beyond the max ahead is refused
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("at", "error"),
    [
        (_local(16, 9), TEXT_TIME_PAST),
        (_local(16, 10).replace(month=12), TEXT_TIME_TOO_FAR),
    ],
)
async def test_bad_slot_is_refused_and_keeps_the_time(at: datetime, error: str) -> None:
    world, _ = _picker_world()
    _scheduled(world, _local(20, 12))
    await _handle(world, _tap(1, _slot(world, at)))
    assert world.messenger.answers[-1].text == error
    assert world.messenger.edits[-1].text == TEXT_CHOOSE_DAY
    assert world.runs.run.scheduled_at == _local(20, 12)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["sched", "days", "other"])
async def test_closed_run_cannot_open_the_picker(kind: str) -> None:
    world, _ = _picker_world()
    world.runs.run = replace(world.runs.run, state=_S.PUBLISHED)
    await _handle(world, _tap(1, world.data(kind)))
    assert world.messenger.answers[-1].text == ANSWER_ALREADY


@pytest.mark.asyncio
async def test_unknown_run_cannot_open_the_picker() -> None:
    world, _ = _picker_world()
    await _handle(world, _tap(1, f"ap:sched:{uuid4()}"))
    assert world.messenger.answers[-1].text == ANSWER_ALREADY


@pytest.mark.asyncio
async def test_closed_run_ignores_day_and_slot_taps() -> None:
    world, _ = _picker_world()
    world.runs.run = replace(world.runs.run, state=_S.REJECTED)
    await _handle(world, _tap(1, _day(world, 20)))
    await _handle(world, _tap(2, _slot(world, _local(20, 18))))
    assert [a.text for a in world.messenger.answers] == [ANSWER_ALREADY] * 2
    assert world.runs.run.state is _S.REJECTED


# Scenario: Publicar agora, Cancelar agendamento and the due tick keep working
@pytest.mark.asyncio
async def test_publish_now_still_works_on_a_rescheduled_run() -> None:
    world, _ = _picker_world()
    _scheduled(world, _local(20, 12))
    await _handle(world, _tap(1, _slot(world, _local(21, 18))))
    await _handle(world, _tap(2, world.data("pubnow")))
    assert world.runs.run.state is _S.PUBLISHING
    assert world.release.ids == [_PROJECT]
    assert world.messenger.edits[-1].text == TEXT_APPROVED


@pytest.mark.asyncio
async def test_without_a_source_the_prior_ranks_the_slots() -> None:
    world = _world(default_publish="next_slot")
    world.clock.at = _local(16, 10)
    await _handle(world, _tap(1, world.data("approve")))
    assert world.runs.run.scheduled_at == _local(16, 12)


# Scenario: Every picker callback fits Telegram's 64 bytes
@pytest.mark.unit
class TestCallbacks:
    def test_picker_callbacks_fit_and_parse(self) -> None:
        run_id = uuid4()
        day = f"ap:d:20261020:{run_id}"
        slot = f"ap:at:{epoch_of(_local(20, 12))}:{run_id}"
        back = f"ap:days:{run_id}"
        assert [len(data.encode()) for data in (day, slot, back)] == [50, 53, 44]
        parsed = parse_callback(day)
        assert parsed is not None
        assert parsed.kind == "d"
        assert parsed.day == date(2026, 10, 20)
        assert parsed.run_id == run_id
        back_parsed = parse_callback(back)
        assert back_parsed is not None
        assert back_parsed.kind == "days"

    @pytest.mark.parametrize(
        "data",
        [
            "ap:d:2026102:{run}",
            "ap:d:202610200:{run}",
            "ap:d:20261340:{run}",
            "ap:d:20261020:{run}x",
            "ap:d::{run}",
            "ap:days:{run}:x",
        ],
    )
    def test_malformed_picker_callbacks_are_none(self, data: str) -> None:
        assert parse_callback(data.format(run=uuid4())) is None
