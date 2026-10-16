"""Approve, publish now, or schedule from Telegram (AE-0370).

Approve offers ``🚀 Publicar agora`` and ``🗓 Agendar`` (or, with
``AUTOPILOT_DEFAULT_PUBLISH=next_slot``, schedules the best recommended slot
of the next seven days directly). A POV run is always auto-scheduled (PR #106
review); without data its Tue/Thu 12:00 prior wins. ``🗓 Agendar`` and
``🗓 Mudar dia/horário`` open the day/time picker (AE-0404); a slot picked on
a scheduled run moves it (``scheduled -> scheduled`` with the new time).
Publish now keeps the AE-0356 path: approve final review, release, and the
worker publishes. Scheduling approves final review but releases nothing: the
run waits in ``scheduled`` and the worker's due tick releases and publishes
it. Every step is a compare-and-set, so a double tap acts once.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from rag_backend.modules.autopilot.application.owner_approval import (
    FinalReviewApproval,
)
from rag_backend.modules.autopilot.application.owner_replies import OwnerReplies
from rag_backend.modules.autopilot.application.owner_steps import (
    APPROVE_FAILED_STEP,
    APPROVE_REFUSED_STEP,
    APPROVE_STEP,
    OwnerStep,
)
from rag_backend.modules.autopilot.application.schedule_picker import (
    PickerDeps,
    SchedulePicker,
    scheduled_text,
)
from rag_backend.modules.autopilot.application.schedule_steps import (
    SCHEDULE_REFUSED_STEP,
    SCHEDULED_PUBLISH_NOW_STEP,
    UNSCHEDULE_STEP,
)
from rag_backend.modules.autopilot.domain.callback_parse import ParsedCallback
from rag_backend.modules.autopilot.domain.gate import ResumeStatus
from rag_backend.modules.autopilot.domain.messages import (
    InlineKeyboard,
    review_keyboard,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.owner_ports import (
    PendingRework,
    PendingReworkStore,
)
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository, Clock
from rag_backend.modules.autopilot.domain.pov_schedule import is_pov_run
from rag_backend.modules.autopilot.domain.recommend import reason_text
from rag_backend.modules.autopilot.domain.schedule import (
    check_choice,
    day_label,
    from_epoch,
    parse_owner_time,
)
from rag_backend.modules.autopilot.domain.schedule_keyboards import (
    publish_choice_keyboard,
    scheduled_keyboard,
)
from rag_backend.modules.autopilot.domain.schedule_ports import ScheduleSignalsSource
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.schedule_constants import (
    ANSWER_CHOOSE,
    ANSWER_SCHEDULED,
    ANSWER_UNSCHEDULED,
    KIND_DAY,
    KIND_DAYS,
    KIND_OTHER_TIME,
    KIND_PUBLISH_NOW,
    KIND_SCHEDULE,
    KIND_SLOT,
    KIND_UNSCHEDULE,
    PUBLISH_MODE_NEXT_SLOT,
    PUBLISH_MODE_NOW,
    REASON_OWNER_RESCHEDULED,
    REASON_OWNER_SCHEDULED,
    SCHEDULE_PENDING_PHASE,
    TEXT_ASK_TIME,
    TEXT_CHOOSE_DAY,
    TEXT_DAY_OUT_OF_RANGE,
    TEXT_PUBLISH_CHOICE,
    TEXT_UNSCHEDULED,
    TIME_ERROR_TEXT,
)
from rag_backend.modules.autopilot.webhook_constants import (
    ANSWER_ALREADY,
    ANSWER_APPROVED,
    KIND_APPROVE,
    TEXT_ALREADY,
    TEXT_APPROVE_FAILED,
    TEXT_APPROVE_REFUSED,
    TEXT_APPROVED,
)

_S = AutopilotRunState
_PICKABLE = frozenset({_S.AWAITING_OWNER, _S.SCHEDULED})
_Handler = Callable[
    ["PublishChoiceActions", WebhookUpdate, ParsedCallback], Awaitable[None]
]


@dataclass(frozen=True, kw_only=True)
class PublishChoiceDeps:
    """Collaborators shared with the owner-action service for one request."""

    runs: AutopilotRunRepository
    pending: PendingReworkStore
    approval: FinalReviewApproval
    clock: Clock
    default_publish: str = PUBLISH_MODE_NOW
    # AE-0404: audience and post engagement for the recommendations.
    signals: ScheduleSignalsSource | None = None


@dataclass(frozen=True, kw_only=True)
class _Choice:
    at: datetime
    reason: str = ""


class PublishChoiceActions:
    """The approve, publish-now, schedule, and cancel buttons."""

    def __init__(self, deps: PublishChoiceDeps, replies: OwnerReplies) -> None:
        self._deps = deps
        self._replies = replies
        self._picker = SchedulePicker(
            PickerDeps(clock=deps.clock, signals=deps.signals), replies
        )

    async def handle(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        """Dispatch one of this module's callback kinds."""
        handler = _HANDLERS[parsed.kind]
        await handler(self, update, parsed)

    async def on_time_text(self, update: WebhookUpdate, pending: PendingRework) -> None:
        """The owner typed a time after ``✏️ Outro horário``."""
        run = await self._pickable(pending.run_id)
        if run is None:
            await self._replies.tell(update, TEXT_ALREADY)
            return
        choice = parse_owner_time(update.text, self._deps.clock.now())
        if choice.at is None:
            await self._deps.pending.put(pending)
            await self._replies.tell(update, TIME_ERROR_TEXT[choice.error or ""])
            await self._replies.ask(update, TEXT_ASK_TIME)
            return
        await self._confirm(update, run, _Choice(at=choice.at))

    async def _approve(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        run = await self._in_state(parsed.run_id, _S.AWAITING_OWNER)
        if run is None:
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        if self._deps.default_publish == PUBLISH_MODE_NEXT_SLOT or is_pov_run(run):
            # AE-0404: the best recommended slot of the next seven days. PR #106
            # review: a POV run is auto-scheduled even when the mode is "now".
            best = await self._picker.best(run)
            choice = _Choice(at=best.at, reason=reason_text(best))
            await self._schedule(update, run, choice)
            return
        await self._replies.answer(update, ANSWER_CHOOSE)
        await self._replies.edit(
            update, TEXT_PUBLISH_CHOICE, publish_choice_keyboard(run.run_id)
        )

    async def _publish_now(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        scheduled = await self._in_state(parsed.run_id, _S.SCHEDULED)
        if scheduled is not None:
            await self._publish_scheduled(update, scheduled)
            return
        run = await self._in_state(parsed.run_id, _S.AWAITING_OWNER)
        if run is None or not await self._apply(run.run_id, APPROVE_STEP):
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        status = await self._deps.approval.approve(run)
        if status is not ResumeStatus.APPLIED:
            await self._refused(update, run, APPROVE_REFUSED_STEP)
            return
        await self._release(update, run)

    async def _publish_scheduled(
        self, update: WebhookUpdate, run: AutopilotRun
    ) -> None:
        """Final review is already approved: release, and the worker publishes."""
        if not await self._apply(run.run_id, SCHEDULED_PUBLISH_NOW_STEP):
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        await self._release(update, run)

    async def _release(self, update: WebhookUpdate, run: AutopilotRun) -> None:
        if not await self._deps.approval.release(run):
            await self._apply(run.run_id, APPROVE_FAILED_STEP)
            await self._replies.finish(update, TEXT_APPROVE_FAILED, TEXT_APPROVE_FAILED)
            return
        await self._replies.finish(update, ANSWER_APPROVED, TEXT_APPROVED)

    async def _schedule_menu(
        self, update: WebhookUpdate, parsed: ParsedCallback
    ) -> None:
        """``🗓 Agendar``, ``🗓 Mudar dia/horário`` and ``← Dias``: the day step."""
        run = await self._pickable(parsed.run_id)
        if run is None:
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        await self._replies.answer(update, TEXT_CHOOSE_DAY)
        await self._picker.show_days(update, run)

    async def _day(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        run = await self._pickable(parsed.run_id)
        if run is None or parsed.day is None:
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        if await self._picker.show_times(update, run, parsed.day):
            await self._replies.answer(update, day_label(parsed.day))
            return
        # A stale keyboard: the day has passed. Offer fresh days.
        await self._replies.answer(update, TEXT_DAY_OUT_OF_RANGE)
        await self._picker.show_days(update, run)

    async def _slot(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        run = await self._pickable(parsed.run_id)
        if run is None:
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        at = from_epoch(parsed.epoch)
        error = check_choice(at, self._deps.clock.now())
        if error is not None:
            # A stale or forged keyboard. Offer fresh days.
            await self._replies.answer(update, TIME_ERROR_TEXT[error])
            await self._picker.show_days(update, run)
            return
        reason = await self._picker.reason_for(run, at)
        await self._confirm(update, run, _Choice(at=at, reason=reason))

    async def _other_time(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        run = await self._pickable(parsed.run_id)
        if run is None:
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        await self._deps.pending.put(
            PendingRework(
                owner_chat_id=update.actor_id,
                run_id=run.run_id,
                phase=SCHEDULE_PENDING_PHASE,
            )
        )
        await self._replies.finish(update, TEXT_ASK_TIME, TEXT_ASK_TIME)
        await self._replies.ask(update, TEXT_ASK_TIME)

    async def _unschedule(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        run = await self._in_state(parsed.run_id, _S.SCHEDULED)
        if run is None or not await self._apply(run.run_id, UNSCHEDULE_STEP):
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        await self._replies.answer(update, ANSWER_UNSCHEDULED)
        await self._replies.edit(update, TEXT_UNSCHEDULED, review_keyboard(run.run_id))

    async def _confirm(
        self, update: WebhookUpdate, run: AutopilotRun, choice: _Choice
    ) -> None:
        """Schedule an awaiting run, or move a scheduled one to the new time."""
        if run.state is not _S.SCHEDULED:
            await self._schedule(update, run, choice)
            return
        if not await self._reschedule(run.run_id, choice.at):
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        await self._replies.answer(update, ANSWER_SCHEDULED)
        text = scheduled_text(choice.at, choice.reason)
        await self._show(update, text, scheduled_keyboard(run.run_id))

    async def _schedule(
        self, update: WebhookUpdate, run: AutopilotRun, choice: _Choice
    ) -> None:
        """Claim ``scheduled`` first, then approve final review; never release."""
        if not await self._to_scheduled(run.run_id, choice.at):
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        status = await self._deps.approval.approve(run)
        if status is not ResumeStatus.APPLIED:
            await self._refused(update, run, SCHEDULE_REFUSED_STEP)
            return
        text = scheduled_text(choice.at, choice.reason)
        await self._replies.answer(update, ANSWER_SCHEDULED)
        await self._show(update, text, scheduled_keyboard(run.run_id))

    async def _refused(
        self, update: WebhookUpdate, run: AutopilotRun, step: OwnerStep
    ) -> None:
        """The editorial approve was refused: keep the review open with buttons."""
        await self._apply(run.run_id, step)
        await self._replies.answer(update, TEXT_APPROVE_FAILED)
        await self._show(update, TEXT_APPROVE_REFUSED, review_keyboard(run.run_id))

    async def _show(
        self, update: WebhookUpdate, text: str, keyboard: InlineKeyboard
    ) -> None:
        """Edit the tapped message; a typed time gets a new message instead."""
        if update.callback_id:
            await self._replies.edit(update, text, keyboard)
            return
        await self._replies.tell(update, text, keyboard)

    async def _in_state(
        self, run_id: UUID, state: AutopilotRunState
    ) -> AutopilotRun | None:
        run = await self._deps.runs.get(run_id)
        if run is None or run.carousel_project_id is None:
            return None
        if run.state is not state:
            return None
        return run

    async def _pickable(self, run_id: UUID) -> AutopilotRun | None:
        """A run under review or already scheduled can pick a time."""
        run = await self._deps.runs.get(run_id)
        if run is None or run.carousel_project_id is None:
            return None
        return run if run.state in _PICKABLE else None

    async def _reschedule(self, run_id: UUID, at: datetime) -> bool:
        """``scheduled -> scheduled`` with the new time; the due tick races safely."""
        return await self._deps.runs.transition(
            TransitionCommand(
                run_id=run_id,
                expected=_S.SCHEDULED,
                new=_S.SCHEDULED,
                reason=REASON_OWNER_RESCHEDULED,
                scheduled_at=at,
            )
        )

    async def _to_scheduled(self, run_id: UUID, at: datetime) -> bool:
        return await self._deps.runs.transition(
            TransitionCommand(
                run_id=run_id,
                expected=_S.AWAITING_OWNER,
                new=_S.SCHEDULED,
                reason=REASON_OWNER_SCHEDULED,
                scheduled_at=at,
            )
        )

    async def _apply(self, run_id: UUID, step: OwnerStep) -> bool:
        return await self._deps.runs.transition(
            TransitionCommand(
                run_id=run_id, expected=step.expected, new=step.new, reason=step.reason
            )
        )


def is_schedule_reply(pending: PendingRework) -> bool:
    """True when the owner's next text is a publish time, not rework feedback."""
    return pending.phase == SCHEDULE_PENDING_PHASE


def _handlers() -> dict[str, _Handler]:
    return {
        KIND_APPROVE: PublishChoiceActions._approve,
        KIND_PUBLISH_NOW: PublishChoiceActions._publish_now,
        KIND_SCHEDULE: PublishChoiceActions._schedule_menu,
        KIND_DAYS: PublishChoiceActions._schedule_menu,
        KIND_DAY: PublishChoiceActions._day,
        KIND_SLOT: PublishChoiceActions._slot,
        KIND_OTHER_TIME: PublishChoiceActions._other_time,
        KIND_UNSCHEDULE: PublishChoiceActions._unschedule,
    }


_HANDLERS = _handlers()
CHOICE_KINDS: frozenset[str] = frozenset(_HANDLERS)
