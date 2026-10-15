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
from rag_backend.modules.autopilot.application.owner_approval import (
    FinalReviewApproval,
)
from rag_backend.modules.autopilot.application.owner_replies import OwnerReplies
from rag_backend.modules.autopilot.application.owner_steps import (
    AUTOFIX_STEP,
    REJECT_STEP,
    RETRY_STEP,
    REWORK_STEP,
    OwnerStep,
)
from rag_backend.modules.autopilot.application.publish_choice import (
    CHOICE_KINDS,
    PublishChoiceActions,
    PublishChoiceDeps,
    is_schedule_reply,
)
from rag_backend.modules.autopilot.application.thesis_actions import (
    ThesisOwnerActions,
    is_thesis_pending,
)
from rag_backend.modules.autopilot.domain.autofix import ContentAutofixer
from rag_backend.modules.autopilot.domain.callback_parse import (
    ParsedCallback,
    parse_callback,
)
from rag_backend.modules.autopilot.domain.gate import (
    EditorialDriver,
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
    CarouselReleaser,
    ForceReplyPrompt,
    OwnerMessenger,
    PendingRework,
    PendingReworkStore,
    UpdateClaimStore,
)
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    CarouselPublishSource,
    Clock,
    TopicCandidateRepository,
)
from rag_backend.modules.autopilot.domain.recovery import ReworkIntent, RunRecoveryStore
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate, is_owner
from rag_backend.modules.autopilot.recovery_constants import NO_RETRY_REASONS
from rag_backend.modules.autopilot.schedule_constants import PUBLISH_MODE_NOW
from rag_backend.modules.autopilot.webhook_constants import (
    ANSWER_ALREADY,
    ANSWER_FIXING,
    ANSWER_MAY_BE_LIVE,
    ANSWER_NOTHING_TO_FIX,
    ANSWER_REJECTED,
    ANSWER_RETRY,
    ANSWER_UNKNOWN,
    AUTOFIX_REWORK_PHASE,
    KIND_CALLBACK,
    KIND_FIX,
    KIND_IGNORED,
    KIND_MESSAGE,
    KIND_PHASE,
    KIND_REJECT,
    KIND_RETRY,
    KIND_REWORK,
    LOG_WEBHOOK,
    TEXT_ALREADY,
    TEXT_CHOOSE_PHASE,
    TEXT_FORCE_REPLY,
    TEXT_MAY_BE_LIVE,
    TEXT_REJECTED,
    TEXT_RETRY,
    TEXT_REWORKING,
    TEXT_SUPERSEDED,
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
    recovery: RunRecoveryStore
    clock: Clock
    owner_chat_id: str
    # AE-0370: skips a second approve after a cancelled schedule.
    carousels: CarouselPublishSource | None = None
    # AE-0370: ``now`` offers publish-now or schedule; ``next_slot`` schedules.
    default_publish: str = PUBLISH_MODE_NOW
    # AE-0367: without it every "Fix issues" tap answers "Nothing to fix".
    autofix: ContentAutofixer | None = None
    # AE-0377: the POV draft thesis lives on the topic candidate.
    topics: TopicCandidateRepository | None = None


class OwnerActionService(ThesisOwnerActions):
    """Apply one claimed update. A second delivery of the same id does nothing."""

    def __init__(self, deps: OwnerActionDeps) -> None:
        self._deps = deps
        self._replies = DeferredOwnerMessenger(deps.messenger)
        self._out = OwnerReplies(self._replies)
        self._choice = PublishChoiceActions(_choice_deps(deps), self._out)

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
        if await self._thesis_callback(update):
            return
        parsed = parse_callback(update.data)
        if parsed is None:
            await self._answer(update, ANSWER_UNKNOWN)
            return
        if parsed.kind in CHOICE_KINDS:
            await self._choice.handle(update, parsed)
            return
        handler = _HANDLERS.get(parsed.kind)
        if handler is None:
            await self._answer(update, ANSWER_UNKNOWN)
            return
        await handler(self, update, parsed)

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

    async def _fix(self, update: WebhookUpdate, parsed: ParsedCallback) -> None:
        """Queue the deterministic repair; the worker tick runs it (AE-0367)."""
        run = await self._awaiting(parsed.run_id)
        if run is None:
            await self._finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        if not await self._fixable(run):
            await self._answer(update, ANSWER_NOTHING_TO_FIX)
            return
        if not await self._apply(run.run_id, AUTOFIX_STEP):
            await self._finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        intent = ReworkIntent(
            run_id=run.run_id, phase=AUTOFIX_REWORK_PHASE, feedback=""
        )
        await self._deps.recovery.queue_rework(intent)
        await self._finish(update, ANSWER_FIXING, TEXT_SUPERSEDED)

    async def _fixable(self, run: AutopilotRun) -> bool:
        if self._deps.autofix is None:
            return False
        issues = await self._deps.autofix.inspect(run.carousel_project_id or "")
        return issues.fixable

    async def _on_text(self, update: WebhookUpdate) -> None:
        feedback = update.text.strip()
        if not feedback:
            return
        pending = await self._deps.pending.take(update.actor_id)
        if pending is None:
            return
        if is_thesis_pending(pending):
            await self._thesis_reply(update, pending)
            return
        if is_schedule_reply(pending):
            await self._choice.on_time_text(update, pending)
            return
        run = await self._awaiting(pending.run_id)
        if run is None or not await self._to_reworking(run.run_id):
            await self._tell(update, TEXT_ALREADY)
            return
        intent = ReworkIntent(run_id=run.run_id, phase=pending.phase, feedback=feedback)
        await self._deps.recovery.queue_rework(intent)
        await self._tell(update, TEXT_REWORKING.format(phase=pending.phase))

    async def _awaiting(self, run_id: UUID) -> AutopilotRun | None:
        run = await self._deps.runs.get(run_id)
        if run is None or run.carousel_project_id is None:
            return None
        if run.state is not AutopilotRunState.AWAITING_OWNER:
            return None
        return run

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
        await self._out.finish(update, answer, text)

    async def _answer(self, update: WebhookUpdate, text: str) -> None:
        await self._out.answer(update, text)

    async def _edit(
        self,
        update: WebhookUpdate,
        text: str,
        keyboard: InlineKeyboard | None,
    ) -> None:
        await self._out.edit(update, text, keyboard)

    async def _tell(self, update: WebhookUpdate, text: str) -> None:
        await self._out.tell(update, text)


def _choice_deps(deps: OwnerActionDeps) -> PublishChoiceDeps:
    approval = FinalReviewApproval(
        editorial=deps.editorial,
        release_port=deps.release,
        carousels=deps.carousels,
    )
    return PublishChoiceDeps(
        runs=deps.runs,
        pending=deps.pending,
        approval=approval,
        clock=deps.clock,
        default_publish=deps.default_publish,
    )


def _delivery(update: WebhookUpdate, deps: OwnerActionDeps) -> TelegramUpdate:
    return TelegramUpdate(update_id=update.update_id, received_at=deps.clock.now())


def _pending(update: WebhookUpdate, run_id: UUID, phase: str) -> PendingRework:
    return PendingRework(owner_chat_id=update.actor_id, run_id=run_id, phase=phase)


def _prompt(update: WebhookUpdate) -> ForceReplyPrompt:
    chat_id = update.chat_id or update.actor_id
    return ForceReplyPrompt(chat_id=chat_id, text=TEXT_FORCE_REPLY)


def _handlers() -> dict[str, _Handler]:
    return {
        KIND_REWORK: OwnerActionService._rework_menu,
        KIND_PHASE: OwnerActionService._choose_phase,
        KIND_REJECT: OwnerActionService._reject,
        KIND_RETRY: OwnerActionService._retry,
        KIND_FIX: OwnerActionService._fix,
    }


_HANDLERS = _handlers()
