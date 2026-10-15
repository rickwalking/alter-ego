"""Approve, publish now, or schedule from Telegram (AE-0370).

Approve offers ``🚀 Publicar agora`` and ``🗓 Agendar`` (or, with
``AUTOPILOT_DEFAULT_PUBLISH=next_slot``, schedules the next slot directly).
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
from rag_backend.modules.autopilot.domain.schedule import (
    check_choice,
    from_epoch,
    local_label,
    next_slots,
    parse_owner_time,
)
from rag_backend.modules.autopilot.domain.schedule_keyboards import (
    SlotMenu,
    publish_choice_keyboard,
    scheduled_keyboard,
    slot_keyboard,
)
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.schedule_constants import (
    ANSWER_CHOOSE,
    ANSWER_SCHEDULED,
    ANSWER_UNSCHEDULED,
    KIND_OTHER_TIME,
    KIND_PUBLISH_NOW,
    KIND_SCHEDULE,
    KIND_SLOT,
    KIND_UNSCHEDULE,
    PUBLISH_MODE_NEXT_SLOT,
    PUBLISH_MODE_NOW,
    REASON_OWNER_SCHEDULED,
    SCHEDULE_PENDING_PHASE,
    TEXT_ASK_TIME,
    TEXT_CHOOSE_SLOT,
    TEXT_PUBLISH_CHOICE,
    TEXT_SCHEDULED,
    TEXT_SCHEDULED_NEXT_SLOT,
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


@dataclass(frozen=True, kw_only=True)
class _Choice:
    at: datetime
    next_slot: bool = False


class PublishChoiceActions:
    """The approve, publish-now, schedule, and cancel buttons."""

    def __init__(self, deps: PublishChoiceDeps, replies: OwnerReplies) -> None:
        self._deps = deps
        self._replies = replies

    async def handle(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        """Dispatch one of this module's callback kinds."""
        handler = _HANDLERS[parsed.kind]
        await handler(self, update, parsed)

    async def on_time_text(self, update: WebhookUpdate, pending: PendingRework) -> None:
        """The owner typed a time after ``✏️ Outro horário``."""
        run = await self._in_state(pending.run_id, _S.AWAITING_OWNER)
        if run is None:
            await self._replies.tell(update, TEXT_ALREADY)
            return
        choice = parse_owner_time(update.text, self._deps.clock.now())
        if choice.at is None:
            await self._deps.pending.put(pending)
            await self._replies.tell(update, TIME_ERROR_TEXT[choice.error or ""])
            await self._replies.ask(update, TEXT_ASK_TIME)
            return
        await self._schedule(update, run, _Choice(at=choice.at))

    async def _approve(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        run = await self._in_state(parsed.run_id, _S.AWAITING_OWNER)
        if run is None:
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        if self._deps.default_publish == PUBLISH_MODE_NEXT_SLOT:
            first = next_slots(self._deps.clock.now())[0]
            await self._schedule(update, run, _Choice(at=first, next_slot=True))
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
        run = await self._in_state(parsed.run_id, _S.AWAITING_OWNER)
        if run is None:
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        await self._replies.answer(update, TEXT_CHOOSE_SLOT)
        await self._show_slots(update, run.run_id)

    async def _slot(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        run = await self._in_state(parsed.run_id, _S.AWAITING_OWNER)
        if run is None:
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        at = from_epoch(parsed.epoch)
        error = check_choice(at, self._deps.clock.now())
        if error is not None:
            # A stale keyboard: the slot has passed. Offer fresh slots.
            await self._replies.answer(update, TIME_ERROR_TEXT[error])
            await self._show_slots(update, run.run_id)
            return
        await self._schedule(update, run, _Choice(at=at))

    async def _other_time(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        run = await self._in_state(parsed.run_id, _S.AWAITING_OWNER)
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
        template = TEXT_SCHEDULED_NEXT_SLOT if choice.next_slot else TEXT_SCHEDULED
        text = template.format(when=local_label(choice.at))
        await self._replies.answer(update, ANSWER_SCHEDULED)
        await self._show(update, text, scheduled_keyboard(run.run_id))

    async def _refused(
        self, update: WebhookUpdate, run: AutopilotRun, step: OwnerStep
    ) -> None:
        """The editorial approve was refused: keep the review open with buttons."""
        await self._apply(run.run_id, step)
        await self._replies.answer(update, TEXT_APPROVE_FAILED)
        await self._show(update, TEXT_APPROVE_REFUSED, review_keyboard(run.run_id))

    async def _show_slots(self, update: WebhookUpdate, run_id: UUID) -> None:
        now = self._deps.clock.now()
        menu = SlotMenu(run_id=run_id, slots=next_slots(now), now=now)
        await self._replies.edit(update, TEXT_CHOOSE_SLOT, slot_keyboard(menu))

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
        KIND_SLOT: PublishChoiceActions._slot,
        KIND_OTHER_TIME: PublishChoiceActions._other_time,
        KIND_UNSCHEDULE: PublishChoiceActions._unschedule,
    }


_HANDLERS = _handlers()
CHOICE_KINDS: frozenset[str] = frozenset(_HANDLERS)
