"""The two-step day/time picker and its recommendations (AE-0404).

Step 1 lists seven days (today when a slot is still open, else tomorrow) and
stars the best ones; step 2 lists the day's four best times with the reason
of each in the message text. The signals (audience, post engagement) are read
once per request; without a source the plan prior alone ranks the slots.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from rag_backend.modules.autopilot.application.owner_replies import OwnerReplies
from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.pov_schedule import is_pov_run
from rag_backend.modules.autopilot.domain.recommend import (
    RecommendQuery,
    ScheduleSignals,
    ScoredSlot,
    best_slot,
    picker_days,
    reason_text,
    score_slot,
    top_times,
)
from rag_backend.modules.autopilot.domain.schedule import (
    day_label,
    schedule_zone,
    when_label,
)
from rag_backend.modules.autopilot.domain.schedule_keyboards import (
    DayMenu,
    TimeMenu,
    day_keyboard,
    time_keyboard,
)
from rag_backend.modules.autopilot.domain.schedule_ports import ScheduleSignalsSource
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.schedule_constants import (
    LOCAL_TIME_FORMAT,
    TEXT_CHOOSE_DAY,
    TEXT_CHOOSE_TIME,
    TEXT_SCHEDULED,
    TEXT_SCHEDULED_REASON,
    TEXT_TIME_LINE,
)


@dataclass(frozen=True, kw_only=True)
class PickerDeps:
    """The clock and, when wired, the recommender's signals."""

    clock: Clock
    signals: ScheduleSignalsSource | None = None


class SchedulePicker:
    """Shows the day and time steps; ranks slots for the auto ``next_slot``."""

    def __init__(self, deps: PickerDeps, replies: OwnerReplies) -> None:
        self._deps = deps
        self._replies = replies
        self._signals: ScheduleSignals | None = None

    async def best(self, run: AutopilotRun) -> ScoredSlot:
        """The best slot within the picker's seven days."""
        return best_slot(await self._query(run))

    async def reason_for(self, run: AutopilotRun, at: datetime) -> str:
        """Why ``at`` was recommended (a picker slot's reason)."""
        return reason_text(score_slot(await self._query(run), at))

    async def show_days(self, update: WebhookUpdate, run: AutopilotRun) -> None:
        """Step 1: the seven day buttons."""
        days = picker_days(await self._query(run))
        menu = DayMenu(run_id=run.run_id, days=days)
        await self._replies.edit(update, TEXT_CHOOSE_DAY, day_keyboard(menu))

    async def show_times(
        self, update: WebhookUpdate, run: AutopilotRun, day: date
    ) -> bool:
        """Step 2 for ``day``; False when the day is not offered any more."""
        query = await self._query(run)
        offered = {option.day for option in picker_days(query)}
        slots = top_times(query, day) if day in offered else ()
        if not slots:
            return False
        menu = TimeMenu(run_id=run.run_id, slots=slots)
        await self._replies.edit(update, times_text(day, slots), time_keyboard(menu))
        return True

    async def _query(self, run: AutopilotRun) -> RecommendQuery:
        if self._signals is None:
            source = self._deps.signals
            self._signals = await source.load() if source else ScheduleSignals()
        return RecommendQuery(
            now=self._deps.clock.now(), pov=is_pov_run(run), signals=self._signals
        )


def times_text(day: date, slots: tuple[ScoredSlot, ...]) -> str:
    """The step-2 text: the day, then one ``HH:MM — reason`` line per time."""
    lines = [
        TEXT_TIME_LINE.format(time=_clock(slot.at), reason=reason_text(slot))
        for slot in slots
    ]
    return "\n".join((TEXT_CHOOSE_TIME.format(day=day_label(day)), *lines))


def scheduled_text(at: datetime, reason: str) -> str:
    """``🗓 Agendado para Ter 20/10 12:00 (reason)``; no reason for a typed time."""
    if not reason:
        return TEXT_SCHEDULED.format(when=when_label(at))
    return TEXT_SCHEDULED_REASON.format(when=when_label(at), reason=reason)


def _clock(at: datetime) -> str:
    return at.astimezone(schedule_zone()).strftime(LOCAL_TIME_FORMAT)
