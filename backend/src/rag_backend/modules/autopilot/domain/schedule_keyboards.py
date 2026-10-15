"""Telegram keyboards for publish-now and scheduling (AE-0370). Pure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from rag_backend.modules.autopilot.domain.messages import (
    InlineButton,
    InlineKeyboard,
    callback_data,
)
from rag_backend.modules.autopilot.domain.schedule import epoch_of, slot_label
from rag_backend.modules.autopilot.schedule_constants import (
    BUTTON_CANCEL_SCHEDULE,
    BUTTON_OTHER_TIME,
    BUTTON_PUBLISH_NOW,
    BUTTON_SCHEDULE,
    CALLBACK_OTHER_TIME_PREFIX,
    CALLBACK_PUBLISH_NOW_PREFIX,
    CALLBACK_SCHEDULE_PREFIX,
    CALLBACK_SLOT_FORMAT,
    CALLBACK_UNSCHEDULE_PREFIX,
)


@dataclass(frozen=True, kw_only=True)
class SlotMenu:
    """The slot buttons for one run, labelled relative to ``now``."""

    run_id: UUID
    slots: tuple[datetime, ...]
    now: datetime


def publish_choice_keyboard(run_id: UUID) -> InlineKeyboard:
    """``🚀 Publicar agora`` and ``🗓 Agendar``."""
    row = (
        _button(BUTTON_PUBLISH_NOW, CALLBACK_PUBLISH_NOW_PREFIX, run_id),
        _button(BUTTON_SCHEDULE, CALLBACK_SCHEDULE_PREFIX, run_id),
    )
    return InlineKeyboard(rows=(row,))


def slot_keyboard(menu: SlotMenu) -> InlineKeyboard:
    """One row per slot, then ``✏️ Outro horário``."""
    rows = tuple(
        (
            InlineButton(
                text=slot_label(slot, menu.now),
                callback_data=callback_data(_slot_prefix(slot), menu.run_id),
            ),
        )
        for slot in menu.slots
    )
    other = _button(BUTTON_OTHER_TIME, CALLBACK_OTHER_TIME_PREFIX, menu.run_id)
    return InlineKeyboard(rows=(*rows, (other,)))


def scheduled_keyboard(run_id: UUID) -> InlineKeyboard:
    """``🚀 Publicar agora`` and ``❌ Cancelar agendamento`` on a scheduled run."""
    row = (
        _button(BUTTON_PUBLISH_NOW, CALLBACK_PUBLISH_NOW_PREFIX, run_id),
        _button(BUTTON_CANCEL_SCHEDULE, CALLBACK_UNSCHEDULE_PREFIX, run_id),
    )
    return InlineKeyboard(rows=(row,))


def _slot_prefix(slot: datetime) -> str:
    return CALLBACK_SLOT_FORMAT.format(epoch=epoch_of(slot))


def _button(text: str, prefix: str, run_id: UUID) -> InlineButton:
    return InlineButton(text=text, callback_data=callback_data(prefix, run_id))
