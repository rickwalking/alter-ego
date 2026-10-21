"""Telegram keyboards for publish-now and scheduling. Pure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from rag_backend.modules.autopilot.domain.messages import (
    InlineButton,
    InlineKeyboard,
    callback_data,
)
from rag_backend.modules.autopilot.domain.recommend import DayOption, ScoredSlot
from rag_backend.modules.autopilot.domain.schedule import (
    day_label,
    epoch_of,
    schedule_zone,
)
from rag_backend.modules.autopilot.recommend_constants import (
    DAY_BUTTONS_PER_ROW,
    STAR,
)
from rag_backend.modules.autopilot.schedule_constants import (
    BUTTON_BACK_TO_DAYS,
    BUTTON_CANCEL_SCHEDULE,
    BUTTON_CHANGE_SCHEDULE,
    BUTTON_OTHER_TIME,
    BUTTON_PUBLISH_NOW,
    BUTTON_SCHEDULE,
    CALLBACK_DAY_DATE_FORMAT,
    CALLBACK_DAY_FORMAT,
    CALLBACK_DAYS_PREFIX,
    CALLBACK_OTHER_TIME_PREFIX,
    CALLBACK_PUBLISH_NOW_PREFIX,
    CALLBACK_SCHEDULE_PREFIX,
    CALLBACK_SLOT_FORMAT,
    CALLBACK_UNSCHEDULE_PREFIX,
    LOCAL_TIME_FORMAT,
)

_TIMES_PER_ROW = 2


@dataclass(frozen=True, kw_only=True)
class DayMenu:
    """The picker's day buttons for one run."""

    run_id: UUID
    days: tuple[DayOption, ...]


@dataclass(frozen=True, kw_only=True)
class TimeMenu:
    """The picker's time buttons for one run and day, best first."""

    run_id: UUID
    slots: tuple[ScoredSlot, ...]


def publish_choice_keyboard(run_id: UUID) -> InlineKeyboard:
    """``🚀 Publicar agora`` and ``🗓 Agendar``."""
    row = (
        _button(BUTTON_PUBLISH_NOW, CALLBACK_PUBLISH_NOW_PREFIX, run_id),
        _button(BUTTON_SCHEDULE, CALLBACK_SCHEDULE_PREFIX, run_id),
    )
    return InlineKeyboard(rows=(row,))


def day_keyboard(menu: DayMenu) -> InlineKeyboard:
    """``Ter 20/10 ⭐`` buttons, three per row."""
    buttons = [
        InlineButton(
            text=_starred(day_label(option.day), starred=option.starred),
            callback_data=callback_data(
                CALLBACK_DAY_FORMAT.format(
                    day=option.day.strftime(CALLBACK_DAY_DATE_FORMAT)
                ),
                menu.run_id,
            ),
        )
        for option in menu.days
    ]
    return InlineKeyboard(rows=_rows(buttons, DAY_BUTTONS_PER_ROW))


def time_keyboard(menu: TimeMenu) -> InlineKeyboard:
    """The best times (the first starred), then ``Outro horário`` and ``← Dias``."""
    buttons = [
        InlineButton(
            text=_starred(_clock(slot.at), starred=index == 0),
            callback_data=callback_data(_slot_prefix(slot.at), menu.run_id),
        )
        for index, slot in enumerate(menu.slots)
    ]
    footer = (
        _button(BUTTON_OTHER_TIME, CALLBACK_OTHER_TIME_PREFIX, menu.run_id),
        _button(BUTTON_BACK_TO_DAYS, CALLBACK_DAYS_PREFIX, menu.run_id),
    )
    return InlineKeyboard(rows=(*_rows(buttons, _TIMES_PER_ROW), footer))


def scheduled_keyboard(run_id: UUID) -> InlineKeyboard:
    """Publish now, change the day/time, or cancel a scheduled run."""
    first = (
        _button(BUTTON_PUBLISH_NOW, CALLBACK_PUBLISH_NOW_PREFIX, run_id),
        _button(BUTTON_CHANGE_SCHEDULE, CALLBACK_SCHEDULE_PREFIX, run_id),
    )
    cancel = _button(BUTTON_CANCEL_SCHEDULE, CALLBACK_UNSCHEDULE_PREFIX, run_id)
    return InlineKeyboard(rows=(first, (cancel,)))


def _rows(
    buttons: list[InlineButton], per_row: int
) -> tuple[tuple[InlineButton, ...], ...]:
    return tuple(
        tuple(buttons[start : start + per_row])
        for start in range(0, len(buttons), per_row)
    )


def _starred(label: str, *, starred: bool) -> str:
    return f"{label} {STAR}" if starred else label


def _clock(at: datetime) -> str:
    return at.astimezone(schedule_zone()).strftime(LOCAL_TIME_FORMAT)


def _slot_prefix(slot: datetime) -> str:
    return CALLBACK_SLOT_FORMAT.format(epoch=epoch_of(slot))


def _button(text: str, prefix: str, run_id: UUID) -> InlineButton:
    return InlineButton(text=text, callback_data=callback_data(prefix, run_id))
