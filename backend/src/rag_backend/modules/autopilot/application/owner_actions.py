"""Owner button presses and rework text become exactly-once run transitions.

Rework stays in ``awaiting_owner`` until the feedback text arrives. The
runner treats ``reworking`` like ``generating`` and would otherwise send
a still-open final review back to the owner before the revise is applied.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

import structlog

from rag_backend.modules.autopilot.application.owner_steps import (
    APPROVE_FAILED_STEP,
    APPROVE_STEP,
    CAP_STEP,
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
    ResumeResult,
    ResumeStatus,
)
from rag_backend.modules.autopilot.domain.messages import (
    InlineKeyboard,
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
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate, is_owner
from rag_backend.modules.autopilot.webhook_constants import (
    ANSWER_ALREADY,
    ANSWER_APPROVED,
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
    TEXT_APPROVED,
    TEXT_CHOOSE_PHASE,
    TEXT_FORCE_REPLY,
    TEXT_REJECTED,
    TEXT_RETRY,
    TEXT_REVISION_CAP,
    TEXT_REWORKING,
)
from rag_backend.modules.editorial.public import (
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
)

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
    clock: Clock
    owner_chat_id: str


@dataclass(frozen=True, kw_only=True)
class _Revise:
    """Feedback that already won the compare-and-set into ``reworking``."""

    update: WebhookUpdate
    run: AutopilotRun
    phase: str
    feedback: str


@dataclass(frozen=True, kw_only=True)
class _Resume:
    """One editorial resume at the current lock version."""

    run: AutopilotRun
    action: str
    feedback: str
    target_phase: str


class OwnerActionService:
    """Apply one claimed update. A second delivery of the same id does nothing."""

    def __init__(self, deps: OwnerActionDeps) -> None:
        self._deps = deps

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
        if not await self._approve_and_release(run):
            await self._fail_publish(run.run_id)
            await self._finish(update, TEXT_APPROVE_FAILED, TEXT_APPROVE_FAILED)
            return
        await self._finish(update, ANSWER_APPROVED, TEXT_APPROVED)

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
        await self._deps.messenger.ask(_prompt(update))

    async def _reject(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        run = await self._awaiting(parsed.run_id)
        if run is None or not await self._to_rejected(run.run_id):
            await self._finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        await self._finish(update, ANSWER_REJECTED, TEXT_REJECTED)

    async def _retry(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
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
        revise = _Revise(
            update=update,
            run=run,
            phase=pending.phase,
            feedback=feedback,
        )
        await self._after_revise(revise)

    async def _after_revise(self, revise: _Revise) -> None:
        result = await self._resume(
            _Resume(
                run=revise.run,
                action=REVIEW_ACTION_REVISE,
                feedback=revise.feedback,
                target_phase=revise.phase,
            )
        )
        if result.status is ResumeStatus.REVISION_CAP:
            await self._to_escalated(revise.run.run_id)
            await self._tell(revise.update, TEXT_REVISION_CAP)
            return
        if result.status is not ResumeStatus.APPLIED:
            await self._tell(revise.update, TEXT_APPROVE_FAILED)
            return
        await self._tell(revise.update, TEXT_REWORKING.format(phase=revise.phase))

    async def _approve_and_release(self, run: AutopilotRun) -> bool:
        result = await self._resume(
            _Resume(run=run, action=REVIEW_ACTION_APPROVE, feedback="", target_phase="")
        )
        if result.status is not ResumeStatus.APPLIED:
            return False
        project_id = run.carousel_project_id or ""
        return await self._deps.release.release(ReleaseCommand(project_id=project_id))

    async def _resume(self, command: _Resume) -> ResumeResult:
        project_id = command.run.carousel_project_id or ""
        snapshot = await self._deps.editorial.read_gate(project_id)
        return await self._deps.editorial.resume(
            ResumeCommand(
                project_id=project_id,
                action=command.action,
                expected_version=snapshot.lock_version,
                feedback=command.feedback,
                phase=GATE_FINAL_REVIEW,
                target_phase=command.target_phase,
            )
        )

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

    async def _to_escalated(self, run_id: UUID) -> bool:
        return await self._apply(run_id, CAP_STEP)

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
        await self._deps.messenger.answer(
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
        await self._deps.messenger.edit(
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
        await self._deps.messenger.tell(OwnerText(chat_id=chat_id, text=text))


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
