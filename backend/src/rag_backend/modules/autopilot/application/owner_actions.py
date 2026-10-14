"""Owner button presses and rework text become exactly-once run transitions.

Rework stays in ``awaiting_owner`` until the feedback text arrives. The
text then moves the run to ``reworking`` and queues phase and feedback on
the row; the worker runner applies the revise, so the webhook never runs
LLM regeneration (QA r1 H4). Replies are buffered and sent only after the
caller commits (``deliver``), or dropped after a rollback (``discard``).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

import structlog

from rag_backend.modules.autopilot.application.deferred_replies import (
    DeferredOwnerMessenger,
)
from rag_backend.modules.autopilot.application.owner_steps import (
    APPROVE_FAILED_STEP,
    APPROVE_REFUSED_STEP,
    APPROVE_STEP,
    REJECT_STEP,
    RETRY_STEP,
    REWORK_STEP,
    OwnerStep,
)
from rag_backend.modules.autopilot.constants import GATE_FINAL_REVIEW
from rag_backend.modules.autopilot.domain.callback_parse import (
    ParsedCallback,
    parse_callback,
)
from rag_backend.modules.autopilot.domain.gate import (
    EditorialDriver,
    ResumeCommand,
    ResumeStatus,
)
from rag_backend.modules.autopilot.domain.messages import (
    InlineKeyboard,
    review_keyboard,
    rework_phase_keyboard,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TelegramUpdate,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.owner_ports import (
    CallbackAnswer,
    CarouselReleaser,
    ForceReplyPrompt,
    MessageEdit,
    OwnerMessenger,
    OwnerText,
    PendingRework,
    PendingReworkStore,
    ReleaseCommand,
    UpdateClaimStore,
)
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository, Clock
from rag_backend.modules.autopilot.domain.recovery import ReworkIntent, RunRecoveryStore
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate, is_owner
from rag_backend.modules.autopilot.recovery_constants import NO_RETRY_REASONS
from rag_backend.modules.autopilot.webhook_constants import (
    ANSWER_ALREADY,
    ANSWER_APPROVED,
    ANSWER_MAY_BE_LIVE,
    ANSWER_REJECTED,
    ANSWER_RETRY,
    ANSWER_UNKNOWN,
    KIND_APPROVE,
    KIND_CALLBACK,
    KIND_IGNORED,
    KIND_MESSAGE,
    KIND_PHASE,
    KIND_REJECT,
    KIND_RETRY,
    KIND_REWORK,
    LOG_WEBHOOK,
    TEXT_ALREADY,
    TEXT_APPROVE_FAILED,
    TEXT_APPROVE_REFUSED,
    TEXT_APPROVED,
    TEXT_CHOOSE_PHASE,
    TEXT_FORCE_REPLY,
    TEXT_MAY_BE_LIVE,
    TEXT_REJECTED,
    TEXT_RETRY,
    TEXT_REWORKING,
)
from rag_backend.modules.editorial.public import REVIEW_ACTION_APPROVE

logger = structlog.get_logger()

_Handler = Callable[
    ["OwnerActionService", WebhookUpdate, ParsedCallback],
    Awaitable[None],
]


@dataclass(frozen=True, kw_only=True)
class OwnerActionDeps:
    """Collaborators for one webhook request. The session is already bound."""

    runs: AutopilotRunRepository
    updates: UpdateClaimStore
    pending: PendingReworkStore
    editorial: EditorialDriver
    release: CarouselReleaser
    messenger: OwnerMessenger
    recovery: RunRecoveryStore
    clock: Clock
    owner_chat_id: str


class OwnerActionService:
    """Apply one claimed update. A second delivery of the same id does nothing."""

    def __init__(self, deps: OwnerActionDeps) -> None:
        self._deps = deps
        self._replies = DeferredOwnerMessenger(deps.messenger)

    async def deliver(self) -> int:
        """Send the replies queued by ``handle``. Call after the commit."""
        return await self._replies.deliver()

    def discard(self) -> int:
        """Drop the queued replies. Call after a rollback."""
        return self._replies.discard()

    async def handle(self, update: WebhookUpdate) -> None:
        """Dedupe, allowlist, then dispatch. Non-owners leave every run unchanged."""
        claimed = await self._deps.updates.claim_update(_delivery(update, self._deps))
        if not claimed or update.kind == KIND_IGNORED:
            return
        if not is_owner(update.actor_id, self._deps.owner_chat_id):
            logger.info(LOG_WEBHOOK, update_id=update.update_id, ignored="not_owner")
            return
        if update.kind == KIND_MESSAGE:
            await self._on_text(update)
            return
        if update.kind == KIND_CALLBACK:
            await self._on_callback(update)

    async def _on_callback(self, update: WebhookUpdate) -> None:
        parsed = parse_callback(update.data)
        if parsed is None:
            await self._answer(update, ANSWER_UNKNOWN)
            return
        handler = _HANDLERS.get(parsed.kind)
        if handler is None:
            await self._answer(update, ANSWER_UNKNOWN)
            return
        await handler(self, update, parsed)

    async def _approve(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        run = await self._awaiting(parsed.run_id)
        if run is None or not await self._to_publishing(run.run_id):
            await self._finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        status = await self._approve_resume(run)
        if status is not ResumeStatus.APPLIED:
            await self._reopen(update, run)
            return
        if not await self._release(run):
            await self._fail_publish(run.run_id)
            await self._finish(update, TEXT_APPROVE_FAILED, TEXT_APPROVE_FAILED)
            return
        await self._finish(update, ANSWER_APPROVED, TEXT_APPROVED)

    async def _reopen(self, update: WebhookUpdate, run: AutopilotRun) -> None:
        """The editorial approve was refused: keep the review open with buttons."""
        await self._apply(run.run_id, APPROVE_REFUSED_STEP)
        await self._answer(update, TEXT_APPROVE_FAILED)
        await self._edit(update, TEXT_APPROVE_REFUSED, review_keyboard(run.run_id))

    async def _rework_menu(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        run = await self._awaiting(parsed.run_id)
        if run is None:
            await self._finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        await self._answer(update, TEXT_CHOOSE_PHASE)
        await self._edit(
            update,
            TEXT_CHOOSE_PHASE,
            rework_phase_keyboard(run.run_id),
        )

    async def _choose_phase(
        self,
        update: WebhookUpdate,
        parsed: ParsedCallback,
    ) -> None:
        run = await self._awaiting(parsed.run_id)
        if run is None:
            await self._finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        await self._deps.pending.put(_pending(update, run.run_id, parsed.phase))
        await self._answer(update, TEXT_FORCE_REPLY)
        await self._edit(update, TEXT_FORCE_REPLY, None)
        await self._replies.ask(_prompt(update))

    async def _reject(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        run = await self._awaiting(parsed.run_id)
        if run is None or not await self._to_rejected(run.run_id):
            await self._finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        await self._finish(update, ANSWER_REJECTED, TEXT_REJECTED)

    async def _retry(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        run = await self._deps.runs.get(parsed.run_id)
        if run is not None and run.state_reason in NO_RETRY_REASONS:
            await self._finish(update, ANSWER_MAY_BE_LIVE, TEXT_MAY_BE_LIVE)
            return
        moved = await self._retry_publish(parsed.run_id)
        if not moved:
            await self._finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        await self._finish(update, ANSWER_RETRY, TEXT_RETRY)

    async def _on_text(self, update: WebhookUpdate) -> None:
        feedback = update.text.strip()
        if not feedback:
            return
        pending = await self._deps.pending.take(update.actor_id)
        if pending is None:
            return
        run = await self._awaiting(pending.run_id)
        if run is None or not await self._to_reworking(run.run_id):
            await self._tell(update, TEXT_ALREADY)
            return
        intent = ReworkIntent(run_id=run.run_id, phase=pending.phase, feedback=feedback)
        await self._deps.recovery.queue_rework(intent)
        await self._tell(update, TEXT_REWORKING.format(phase=pending.phase))

    async def _approve_resume(self, run: AutopilotRun) -> ResumeStatus:
        project_id = run.carousel_project_id or ""
        snapshot = await self._deps.editorial.read_gate(project_id)
        result = await self._deps.editorial.resume(
            ResumeCommand(
                project_id=project_id,
                action=REVIEW_ACTION_APPROVE,
                expected_version=snapshot.lock_version,
                feedback="",
                phase=GATE_FINAL_REVIEW,
            )
        )
        return result.status

    async def _release(self, run: AutopilotRun) -> bool:
        project_id = run.carousel_project_id or ""
        return await self._deps.release.release(ReleaseCommand(project_id=project_id))

    async def _awaiting(self, run_id: UUID) -> AutopilotRun | None:
        run = await self._deps.runs.get(run_id)
        if run is None or run.carousel_project_id is None:
            return None
        if run.state is not AutopilotRunState.AWAITING_OWNER:
            return None
        return run

    async def _to_publishing(self, run_id: UUID) -> bool:
        return await self._apply(run_id, APPROVE_STEP)

    async def _fail_publish(self, run_id: UUID) -> bool:
        return await self._apply(run_id, APPROVE_FAILED_STEP)

    async def _to_rejected(self, run_id: UUID) -> bool:
        return await self._apply(run_id, REJECT_STEP)

    async def _retry_publish(self, run_id: UUID) -> bool:
        return await self._apply(run_id, RETRY_STEP)

    async def _to_reworking(self, run_id: UUID) -> bool:
        return await self._apply(run_id, REWORK_STEP)

    async def _apply(self, run_id: UUID, step: OwnerStep) -> bool:
        command = TransitionCommand(
            run_id=run_id,
            expected=step.expected,
            new=step.new,
            reason=step.reason,
        )
        return await self._deps.runs.transition(command)

    async def _finish(self, update: WebhookUpdate, answer: str, text: str) -> None:
        await self._answer(update, answer)
        await self._edit(update, text, None)

    async def _answer(self, update: WebhookUpdate, text: str) -> None:
        if not update.callback_id:
            return
        await self._replies.answer(
            CallbackAnswer(callback_id=update.callback_id, text=text)
        )

    async def _edit(
        self,
        update: WebhookUpdate,
        text: str,
        keyboard: InlineKeyboard | None,
    ) -> None:
        if update.message_id is None or not update.chat_id:
            return
        await self._replies.edit(
            MessageEdit(
                chat_id=update.chat_id,
                message_id=update.message_id,
                text=text,
                keyboard=keyboard,
            )
        )

    async def _tell(self, update: WebhookUpdate, text: str) -> None:
        chat_id = update.chat_id or update.actor_id
        if not chat_id:
            return
        await self._replies.tell(OwnerText(chat_id=chat_id, text=text))


def _delivery(update: WebhookUpdate, deps: OwnerActionDeps) -> TelegramUpdate:
    return TelegramUpdate(update_id=update.update_id, received_at=deps.clock.now())


def _pending(update: WebhookUpdate, run_id: UUID, phase: str) -> PendingRework:
    return PendingRework(owner_chat_id=update.actor_id, run_id=run_id, phase=phase)


def _prompt(update: WebhookUpdate) -> ForceReplyPrompt:
    chat_id = update.chat_id or update.actor_id
    return ForceReplyPrompt(chat_id=chat_id, text=TEXT_FORCE_REPLY)


def _handlers() -> dict[str, _Handler]:
    return {
        KIND_APPROVE: OwnerActionService._approve,
        KIND_REWORK: OwnerActionService._rework_menu,
        KIND_PHASE: OwnerActionService._choose_phase,
        KIND_REJECT: OwnerActionService._reject,
        KIND_RETRY: OwnerActionService._retry,
    }


_HANDLERS = _handlers()
