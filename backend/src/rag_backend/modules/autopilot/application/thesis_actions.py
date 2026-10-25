"""Owner thesis buttons and the edited-thesis reply (ADR-0021 D10).

A mixin for ``OwnerActionService`` so the webhook keeps one entry point, one
owner allowlist and one deferred-reply buffer. Confirm and the edit reply use
one compare-and-set (``confirm_thesis``), so a double tap starts generation
once; discard moves ``awaiting_thesis`` to ``rejected``. A confirmed thesis shows
the run's place in the generation queue and its estimated start.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.application.deferred_replies import (
    DeferredOwnerMessenger,
)
from rag_backend.modules.autopilot.domain.messages import InlineKeyboard
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    ThesisConfirmCommand,
    TopicCandidate,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.owner_ports import (
    ForceReplyPrompt,
    PendingRework,
    PendingReworkStore,
)
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    Clock,
    TopicCandidateRepository,
)
from rag_backend.modules.autopilot.domain.queue_position import (
    QueueControl,
    position_of,
    position_text,
)
from rag_backend.modules.autopilot.domain.thesis import (
    ThesisCallback,
    clean_thesis,
    parse_thesis_callback,
)
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.pov_constants import (
    ANSWER_THESIS_CONFIRMED,
    ANSWER_THESIS_DISCARDED,
    ANSWER_THESIS_EDIT,
    KIND_THESIS_CONFIRM,
    KIND_THESIS_DISCARD,
    REASON_THESIS_CONFIRMED,
    REASON_THESIS_DISCARDED,
    TEXT_THESIS_ALREADY,
    TEXT_THESIS_CONFIRMED,
    TEXT_THESIS_DISCARDED,
    TEXT_THESIS_EDIT,
    TEXT_THESIS_TOO_LONG,
    THESIS_PENDING_PHASE,
)
from rag_backend.modules.autopilot.queue_constants import TEXT_THESIS_CONFIRMED_QUEUED


class _ThesisDeps(Protocol):
    @property
    def runs(self) -> AutopilotRunRepository: ...

    @property
    def pending(self) -> PendingReworkStore: ...

    @property
    def topics(self) -> TopicCandidateRepository | None: ...

    @property
    def clock(self) -> Clock: ...

    @property
    def queue(self) -> QueueControl | None: ...


class _Host(Protocol):
    """What the mixin needs from ``OwnerActionService``."""

    @property
    def _deps(self) -> _ThesisDeps: ...

    @property
    def _replies(self) -> DeferredOwnerMessenger: ...

    async def _answer(self, update: WebhookUpdate, text: str) -> None: ...

    async def _edit(
        self, update: WebhookUpdate, text: str, keyboard: InlineKeyboard | None
    ) -> None: ...

    async def _finish(self, update: WebhookUpdate, answer: str, text: str) -> None: ...

    async def _tell(self, update: WebhookUpdate, text: str) -> None: ...


class ThesisOwnerActions:
    """Confirm, edit (ForceReply) or discard a POV run's thesis."""

    async def _thesis_callback(self: _Host, update: WebhookUpdate) -> bool:
        """Handle a thesis button. False when ``update`` is not one."""
        parsed = parse_thesis_callback(update.data)
        if parsed is None:
            return False
        run = await _awaiting_thesis(self._deps.runs, parsed.run_id)
        if run is None:
            await self._finish(update, TEXT_THESIS_ALREADY, TEXT_THESIS_ALREADY)
            return True
        if parsed.kind == KIND_THESIS_CONFIRM:
            await _confirm_draft(self, update, run)
        elif parsed.kind == KIND_THESIS_DISCARD:
            await _discard(self, update, parsed)
        else:
            await _ask_edit(self, update, run)
        return True

    async def _thesis_reply(
        self: _Host, update: WebhookUpdate, pending: PendingRework
    ) -> None:
        """The owner's own thesis, typed after "Editar"."""
        thesis = clean_thesis(update.text)
        if thesis is None:
            await self._deps.pending.put(pending)
            await self._tell(update, TEXT_THESIS_TOO_LONG)
            return
        confirmed = await self._deps.runs.confirm_thesis(
            ThesisConfirmCommand(
                run_id=pending.run_id, thesis=thesis, reason=REASON_THESIS_CONFIRMED
            )
        )
        text = (
            await _confirmed_text(self, pending.run_id, thesis)
            if confirmed
            else TEXT_THESIS_ALREADY
        )
        await self._tell(update, text)


def is_thesis_pending(pending: PendingRework) -> bool:
    """True when the owner's next text is an edited thesis."""
    return pending.phase == THESIS_PENDING_PHASE


async def _awaiting_thesis(
    runs: AutopilotRunRepository, run_id: UUID
) -> AutopilotRun | None:
    run = await runs.get(run_id)
    if run is None or run.state is not AutopilotRunState.AWAITING_THESIS:
        return None
    return run


async def _draft(host: _Host, run: AutopilotRun) -> TopicCandidate | None:
    topics = host._deps.topics
    if topics is None:
        return None
    return await topics.get_topic(run.topic_candidate_id)


async def _confirm_draft(host: _Host, update: WebhookUpdate, run: AutopilotRun) -> None:
    topic = await _draft(host, run)
    thesis = clean_thesis(topic.thesis_draft or "") if topic is not None else None
    if thesis is None:
        await _ask_edit(host, update, run)
        return
    confirmed = await host._deps.runs.confirm_thesis(
        ThesisConfirmCommand(
            run_id=run.run_id, thesis=thesis, reason=REASON_THESIS_CONFIRMED
        )
    )
    if not confirmed:
        await host._finish(update, TEXT_THESIS_ALREADY, TEXT_THESIS_ALREADY)
        return
    text = await _confirmed_text(host, run.run_id, thesis)
    await host._finish(update, ANSWER_THESIS_CONFIRMED, text)


async def _confirmed_text(host: _Host, run_id: UUID, thesis: str) -> str:
    """The confirmation with the run's queue position, when the queue is wired."""
    queue = host._deps.queue
    snapshot = await queue.snapshot() if queue is not None else None
    position = (
        position_of(snapshot, run_id, host._deps.clock.now()) if snapshot else None
    )
    if position is None:
        return TEXT_THESIS_CONFIRMED.format(thesis=thesis)
    return TEXT_THESIS_CONFIRMED_QUEUED.format(
        thesis=thesis, position=position_text(position)
    )


async def _discard(host: _Host, update: WebhookUpdate, parsed: ThesisCallback) -> None:
    moved = await host._deps.runs.transition(
        TransitionCommand(
            run_id=parsed.run_id,
            expected=AutopilotRunState.AWAITING_THESIS,
            new=AutopilotRunState.REJECTED,
            reason=REASON_THESIS_DISCARDED,
        )
    )
    if not moved:
        await host._finish(update, TEXT_THESIS_ALREADY, TEXT_THESIS_ALREADY)
        return
    await host._finish(update, ANSWER_THESIS_DISCARDED, TEXT_THESIS_DISCARDED)


async def _ask_edit(host: _Host, update: WebhookUpdate, run: AutopilotRun) -> None:
    await host._deps.pending.put(
        PendingRework(
            owner_chat_id=update.actor_id,
            run_id=run.run_id,
            phase=THESIS_PENDING_PHASE,
        )
    )
    await host._answer(update, ANSWER_THESIS_EDIT)
    chat_id = update.chat_id or update.actor_id
    await host._replies.ask(ForceReplyPrompt(chat_id=chat_id, text=TEXT_THESIS_EDIT))


__all__ = ["ThesisOwnerActions", "is_thesis_pending"]
