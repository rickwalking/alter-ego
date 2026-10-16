"""Scheduling rules, callbacks, keyboards, and copy (AE-0370).

Gherkin: tests/features/autopilot_scheduled_publish.feature
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from rag_backend.modules.autopilot.domain.callback_parse import parse_callback
from rag_backend.modules.autopilot.domain.messages import StatusCopy, status_text
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionCommand,
    TransitionPair,
)
from rag_backend.modules.autopilot.domain.publish import PostExtras
from rag_backend.modules.autopilot.domain.published_copy import (
    extras_payload,
    post_extras_of,
    published_text,
    with_late,
)
from rag_backend.modules.autopilot.domain.recommend import (
    RecommendQuery,
    ScheduleSignals,
    best_slot,
    picker_days,
    top_times,
)
from rag_backend.modules.autopilot.domain.schedule import (
    check_choice,
    clears_schedule,
    day_label,
    epoch_of,
    from_epoch,
    late_minutes,
    parse_owner_time,
    when_label,
)
from rag_backend.modules.autopilot.domain.schedule_keyboards import (
    DayMenu,
    TimeMenu,
    day_keyboard,
    publish_choice_keyboard,
    scheduled_keyboard,
    time_keyboard,
)
from rag_backend.modules.autopilot.domain.state_machine import assert_allowed
from rag_backend.modules.autopilot.notify_constants import (
    KIND_EXPIRED,
    TEXT_EXPIRED,
)
from rag_backend.modules.autopilot.schedule_constants import (
    ERR_TIME_FORMAT,
    ERR_TIME_PAST,
    ERR_TIME_TOO_FAR,
    REASON_OWNER_UNSCHEDULED,
    REASON_SCHEDULE_DUE,
    REASON_SCHEDULE_WITHDRAWN,
    TEXT_SCHEDULE_WITHDRAWN,
)

_SP = ZoneInfo("America/Sao_Paulo")
_S = AutopilotRunState


def _local(day: int, hour: int, minute: int = 0, month: int = 10) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=_SP).astimezone(UTC)


def local_label(at: datetime) -> str:
    return at.astimezone(_SP).strftime("%d/%m %H:%M")


def _first(now: datetime) -> datetime:
    """AE-0404: the auto slot of a Radar run without insights."""
    return best_slot(RecommendQuery(now=now, pov=False, signals=ScheduleSignals())).at


# Scenario: Without insights a Radar run keeps the default slots (AE-0404)
def test_first_slot_from_the_morning() -> None:
    first = _first(_local(15, 10))
    assert local_label(first) == "15/10 12:00"
    assert first.tzinfo is UTC


# Scenario: A slot less than 15 minutes away is skipped
@pytest.mark.parametrize(
    ("hour", "minute", "first"),
    [(11, 44, "15/10 12:00"), (11, 45, "15/10 12:00"), (11, 46, "15/10 18:00")],
)
def test_fifteen_minute_lead(hour: int, minute: int, first: str) -> None:
    assert local_label(_first(_local(15, hour, minute))) == first


# Scenario: Slots roll over to the next day
def test_slots_roll_over_after_the_last_slot() -> None:
    assert local_label(_first(_local(15, 22))) == "16/10 12:00"


# Scenario: Slots are computed in America/Sao_Paulo, whatever the server zone
def test_slots_use_sao_paulo_not_utc() -> None:
    now = datetime(2026, 10, 15, 14, 0, tzinfo=UTC)  # 11:00 in Sao Paulo
    first = _first(now)
    assert local_label(first) == "15/10 12:00"
    assert first == datetime(2026, 10, 15, 15, 0, tzinfo=UTC)


def test_day_and_when_labels() -> None:
    assert day_label(_local(20, 12).astimezone(_SP).date()) == "Ter 20/10"
    assert when_label(_local(18, 9, 5)) == "Dom 18/10 09:05"


# Scenario Outline: The owner types a valid time
@pytest.mark.parametrize(
    ("text", "local"),
    [
        ("19:30", "15/10 19:30"),
        ("09:15", "16/10 09:15"),
        (" 9:05 ", "16/10 09:05"),
        ("20/10 08:00", "20/10 08:00"),
        ("1/11  7:30", "01/11 07:30"),
    ],
)
def test_valid_owner_times(text: str, local: str) -> None:
    choice = parse_owner_time(text, _local(15, 10))
    assert choice.error is None
    assert choice.at is not None
    assert local_label(choice.at) == local


def test_hh_mm_equal_to_now_means_tomorrow() -> None:
    choice = parse_owner_time("10:00", _local(15, 10))
    assert choice.at == _local(16, 10)


# Scenario Outline: The owner types an invalid time
@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("amanhã", ERR_TIME_FORMAT),
        ("", ERR_TIME_FORMAT),
        ("25:00", ERR_TIME_FORMAT),
        ("10:60", ERR_TIME_FORMAT),
        ("31/02 10:00", ERR_TIME_FORMAT),
        ("15/13 10:00", ERR_TIME_FORMAT),
        ("15/10 24:00", ERR_TIME_FORMAT),
        ("15/10 09:00", ERR_TIME_PAST),
        ("15/10 10:00", ERR_TIME_PAST),
        ("20/12 10:00", ERR_TIME_TOO_FAR),
    ],
)
def test_invalid_owner_times(text: str, error: str) -> None:
    choice = parse_owner_time(text, _local(15, 10))
    assert choice.at is None
    assert choice.error == error


def test_new_year_date_means_next_january() -> None:
    now = datetime(2026, 12, 30, 10, 0, tzinfo=_SP)
    choice = parse_owner_time("02/01 09:00", now)
    assert choice.at == datetime(2027, 1, 2, 9, 0, tzinfo=_SP)


def test_past_feb_29_with_no_leap_next_year_is_past() -> None:
    now = datetime(2028, 3, 1, 10, 0, tzinfo=_SP)
    assert parse_owner_time("29/02 09:00", now).error == ERR_TIME_PAST


def test_check_choice_bounds() -> None:
    now = _local(15, 10)
    assert check_choice(now, now) == ERR_TIME_PAST
    assert check_choice(now + timedelta(minutes=1), now) is None
    assert check_choice(now + timedelta(days=30), now) is None
    assert check_choice(now + timedelta(days=30, seconds=1), now) == ERR_TIME_TOO_FAR


# Scenario: A late run publishes anyway and says how late
def test_late_minutes_threshold() -> None:
    due = _local(15, 18)
    assert late_minutes(None, due) is None
    assert late_minutes(due, due + timedelta(minutes=10)) is None
    assert late_minutes(due, due + timedelta(minutes=10, seconds=59)) is None
    assert late_minutes(due, due + timedelta(minutes=11)) == 11
    assert late_minutes(due, due + timedelta(minutes=25)) == 25


def test_epoch_round_trip() -> None:
    at = _local(15, 18)
    assert from_epoch(epoch_of(at)) == at


def test_clears_schedule_only_when_leaving_scheduled_by_hand() -> None:
    run_id = uuid4()

    def command(expected: AutopilotRunState, reason: str) -> TransitionCommand:
        return TransitionCommand(
            run_id=run_id, expected=expected, new=_S.PUBLISHING, reason=reason
        )

    assert clears_schedule(command(_S.SCHEDULED, REASON_OWNER_UNSCHEDULED))
    assert not clears_schedule(command(_S.SCHEDULED, REASON_SCHEDULE_DUE))
    assert not clears_schedule(command(_S.AWAITING_OWNER, REASON_OWNER_UNSCHEDULED))


@pytest.mark.parametrize(
    ("expected", "new"),
    [
        (_S.AWAITING_OWNER, _S.SCHEDULED),
        (_S.SCHEDULED, _S.PUBLISHING),
        (_S.SCHEDULED, _S.AWAITING_OWNER),
        (_S.SCHEDULED, _S.EXPIRED),
    ],
)
def test_state_machine_allows_schedule_pairs(
    expected: AutopilotRunState, new: AutopilotRunState
) -> None:
    assert_allowed(TransitionPair(expected=expected, new=new))


def test_state_machine_refuses_scheduled_to_published() -> None:
    from rag_backend.modules.autopilot.domain.exceptions import (
        InvalidAutopilotTransition,
    )

    with pytest.raises(InvalidAutopilotTransition):
        assert_allowed(TransitionPair(expected=_S.SCHEDULED, new=_S.PUBLISHED))


# Scenario: Approve offers publish now or schedule
def test_callbacks_parse_and_fit_64_bytes() -> None:
    run_id = uuid4()
    now = _local(15, 10)
    keyboards = (
        publish_choice_keyboard(run_id),
        scheduled_keyboard(run_id),
        day_keyboard(DayMenu(run_id=run_id, days=picker_days(_query(now)))),
        time_keyboard(
            TimeMenu(run_id=run_id, slots=top_times(_query(now), _local(16, 9).date()))
        ),
    )
    for keyboard in keyboards:
        for row in keyboard.rows:
            for button in row:
                assert len(button.callback_data.encode()) <= 64
                parsed = parse_callback(button.callback_data)
                assert parsed is not None
                assert parsed.run_id == run_id


def test_choice_and_scheduled_buttons() -> None:
    run_id = uuid4()
    choice = publish_choice_keyboard(run_id).rows[0]
    assert [b.text for b in choice] == [
        "\U0001f680 Publicar agora",
        "\U0001f5d3 Agendar",
    ]
    assert [b.callback_data for b in choice] == [
        f"ap:pubnow:{run_id}",
        f"ap:sched:{run_id}",
    ]
    scheduled = [b for row in scheduled_keyboard(run_id).rows for b in row]
    assert [b.callback_data for b in scheduled] == [
        f"ap:pubnow:{run_id}",
        f"ap:sched:{run_id}",
        f"ap:unsched:{run_id}",
    ]
    assert scheduled[1].text == "\U0001f5d3 Mudar dia/horário"
    assert scheduled[2].text == "❌ Cancelar agendamento"


def _query(now: datetime) -> RecommendQuery:
    return RecommendQuery(now=now, pov=False, signals=ScheduleSignals())


def test_time_keyboard_rows_and_slot_callback() -> None:
    run_id = uuid4()
    slots = top_times(_query(_local(15, 10)), _local(15, 12).astimezone(_SP).date())
    rows = time_keyboard(TimeMenu(run_id=run_id, slots=slots)).rows
    assert [[b.text for b in row] for row in rows] == [
        ["12:00 ⭐", "18:00"],
        ["21:00", "11:00"],
        ["✏️ Outro horário", "← Dias"],
    ]
    parsed = parse_callback(rows[0][1].callback_data)
    assert parsed is not None
    assert parsed.kind == "at"
    assert from_epoch(parsed.epoch) == _local(15, 18)
    assert rows[2][0].callback_data == f"ap:other:{run_id}"
    assert rows[2][1].callback_data == f"ap:days:{run_id}"


@pytest.mark.parametrize(
    "data",
    [
        "ap:at::{run}",
        "ap:at:12345678901:{run}",
        "ap:at:abc:{run}",
        "ap:sched:{run}x",
        "ap:pubnow:not-a-uuid",
    ],
)
def test_malformed_schedule_callbacks_are_none(data: str) -> None:
    assert parse_callback(data.format(run=uuid4())) is None


# Scenario: A late run publishes anyway and says how late
def test_published_text_carries_the_delay() -> None:
    extras = with_late(None, 25)
    assert extras is not None
    text = published_text("https://ig/p/1", extras)
    assert text == "✅ Publicado: https://ig/p/1 (publicado com atraso de 25 min)"


def test_delay_keeps_story_and_music_lines() -> None:
    story = PostExtras(story_status="published", story_error=None, music_style="x")
    extras = with_late(story, 12)
    assert extras is not None
    lines = published_text("", extras).split("\n")
    assert lines[0] == "✅ Publicado (publicado com atraso de 12 min)"
    assert len(lines) == 3


def test_no_delay_leaves_extras_unchanged() -> None:
    story = PostExtras(story_status="published", story_error=None, music_style="x")
    assert with_late(story, None) is story
    assert with_late(None, None) is None
    assert "atraso" not in published_text("https://ig/p/1", story)


def test_delay_round_trips_through_the_outbox_payload() -> None:
    extras = with_late(None, 30)
    restored = post_extras_of(extras_payload(extras))
    assert restored == extras
    payload = extras_payload(
        PostExtras(story_status="", story_error=None, music_style="")
    )
    payload["late_minutes"] = True
    restored_bool = post_extras_of(payload)
    assert restored_bool is not None
    assert restored_bool.late_minutes is None


# Scenario: A scheduled carousel that is no longer approved expires
def test_expired_notice_text_by_reason() -> None:
    def copy(reason: str) -> StatusCopy:
        return StatusCopy(reason=reason, link="", permalink="", days_remaining=None)

    assert status_text(KIND_EXPIRED, copy(REASON_SCHEDULE_WITHDRAWN)) == (
        TEXT_SCHEDULE_WITHDRAWN
    )
    assert status_text(KIND_EXPIRED, copy("owner_review_expired")) == TEXT_EXPIRED
