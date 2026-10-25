"""Owner queue buttons: "Aprovar todas", dead-letter retry/discard, "Gerar agora".

A mixin for ``OwnerActionService`` (one webhook entry point, one owner allowlist,
one deferred-reply buffer). Every action is a compare-and-set, so a second tap
changes nothing and answers "already resolved". Positions are read in the same
transaction, after the change, from the generation queue's FIFO order.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID, uuid4

from rag_backend.modules.autopilot.application.run_revive import (
    ReviveDependencies,
    revive,
)
from rag_backend.modules.autopilot.domain.backlog import (
    BacklogStore,
    GenerateNowCommand,
)
from rag_backend.modules.autopilot.domain.dead_letter import (
    DeadLetterRuns,
    is_dead_letter,
)
from rag_backend.modules.autopilot.domain.messages import InlineKeyboard
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    ThesisConfirmCommand,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    Clock,
    TopicCandidateRepository,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.queue_callback import parse_queue_callback
from rag_backend.modules.autopilot.domain.queue_position import (
    QueueControl,
    QueueSnapshot,
    joined_titles,
    local_time,
    position_of,
    position_text,
)
from rag_backend.modules.autopilot.domain.thesis import clean_thesis
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.pov_constants import REASON_THESIS_CONFIRMED
from rag_backend.modules.autopilot.queue_constants import (
    ANSWER_APPROVED,
    ANSWER_DEAD_DISCARDED,
    ANSWER_DEAD_RETRIED,
    ANSWER_GENERATED_NOW,
    APPROVE_ALL_LIMIT,
    CALLBACK_APPROVE_ALL,
    KIND_DEAD_DISCARD,
    KIND_DEAD_RETRY,
    KIND_GENERATE_NOW,
    REASON_DEAD_DISCARD,
    REASON_DEAD_RETRY,
    TEXT_APPROVED_HEADER,
    TEXT_APPROVED_LINE,
    TEXT_APPROVED_NEED_EDIT,
    TEXT_APPROVED_NONE,
    TEXT_BATCH_LINE,
    TEXT_DEAD_DISCARDED,
    TEXT_DEAD_RETRIED,
    TEXT_DEAD_RETRIED_PLAIN,
    TEXT_GENERATED_NOW,
    TEXT_GENERATED_NOW_PLAIN,
    TEXT_QUEUE_ALREADY,
    THESIS_BATCH_NOTICE_KEY,
)


class _QueueDeps(Protocol):
    @property
    def runs(self) -> AutopilotRunRepository: ...

    @property
    def topics(self) -> TopicCandidateRepository | None: ...

    @property
    def clock(self) -> Clock: ...

    @property
    def queue(self) -> QueueControl | None: ...

    @property
    def backlog(self) -> BacklogStore | None: ...

    @property
    def dead_letters(self) -> DeadLetterRuns | None: ...


class _Host(Protocol):
    """What the mixin needs from ``OwnerActionService``."""

    @property
    def _deps(self) -> _QueueDeps: ...

    async def _answer(self, update: WebhookUpdate, text: str) -> None: ...

    async def _edit(
        self, update: WebhookUpdate, text: str, keyboard: InlineKeyboard | None
    ) -> None: ...

    async def _finish(self, update: WebhookUpdate, answer: str, text: str) -> None: ...

    async def _tell(self, update: WebhookUpdate, text: str) -> None: ...


class QueueOwnerActions:
    """Approve every waiting thesis, retry or discard a dead letter, generate now."""

    async def _queue_callback(self: _Host, update: WebhookUpdate) -> bool:
        """Handle a queue button. False when ``update`` is not one."""
        if update.data == CALLBACK_APPROVE_ALL:
            await _approve_all(self, update)
            return True
        parsed = parse_queue_callback(update.data)
        if parsed is None:
            return False
        if parsed.kind == KIND_DEAD_RETRY:
            await _retry(self, update, parsed.target)
        elif parsed.kind == KIND_DEAD_DISCARD:
            await _discard(self, update, parsed.target)
        elif parsed.kind == KIND_GENERATE_NOW:
            await _generate_now(self, update, parsed.target)
        return True


async def _snapshot(host: _Host) -> QueueSnapshot | None:
    queue = host._deps.queue
    return await queue.snapshot() if queue is not None else None


async def _position(host: _Host, run_id: UUID) -> str | None:
    snapshot = await _snapshot(host)
    if snapshot is None:
        return None
    position = position_of(snapshot, run_id, host._deps.clock.now())
    return position_text(position) if position is not None else None


async def _approve_all(host: _Host, update: WebhookUpdate) -> None:
    query = RunListQuery(
        state=AutopilotRunState.AWAITING_THESIS, limit=APPROVE_ALL_LIMIT
    )
    confirmed: list[tuple[UUID, str]] = []
    need_edit: list[str] = []
    for run in await host._deps.runs.list_by_state(query):
        if THESIS_BATCH_NOTICE_KEY in run.notice_log.statuses:
            await _approve_one(host, run, (confirmed, need_edit))
    if not confirmed and not need_edit:
        await host._finish(update, TEXT_QUEUE_ALREADY, TEXT_APPROVED_NONE)
        return
    lines = await _approved_lines(host, confirmed)
    if need_edit:
        lines.append(TEXT_APPROVED_NEED_EDIT.format(titles=joined_titles(need_edit)))
    header = TEXT_APPROVED_HEADER.format(count=len(confirmed))
    await host._finish(update, ANSWER_APPROVED, "\n".join((header, *lines)))


async def _approve_one(
    host: _Host,
    run: AutopilotRun,
    outcome: tuple[list[tuple[UUID, str]], list[str]],
) -> None:
    confirmed, need_edit = outcome
    topics = host._deps.topics
    topic = await topics.get_topic(run.topic_candidate_id) if topics else None
    if topic is None:
        return
    thesis = clean_thesis(topic.thesis_draft or "")
    if thesis is None:
        need_edit.append(topic.title)
        return
    command = ThesisConfirmCommand(
        run_id=run.run_id, thesis=thesis, reason=REASON_THESIS_CONFIRMED
    )
    if await host._deps.runs.confirm_thesis(command):
        confirmed.append((run.run_id, thesis))


async def _approved_lines(host: _Host, confirmed: list[tuple[UUID, str]]) -> list[str]:
    snapshot = await _snapshot(host)
    now = host._deps.clock.now()
    lines: list[str] = []
    for index, (run_id, thesis) in enumerate(confirmed, 1):
        position = position_of(snapshot, run_id, now) if snapshot else None
        if position is None:
            lines.append(TEXT_BATCH_LINE.format(index=index, thesis=thesis))
            continue
        lines.append(
            TEXT_APPROVED_LINE.format(
                index=index,
                thesis=thesis,
                position=position.position,
                total=position.total,
                eta=local_time(position.eta),
            )
        )
    return lines


async def _retry(host: _Host, update: WebhookUpdate, run_id: UUID) -> None:
    run = await host._deps.runs.get(run_id)
    queued_id = await _retried_run(host, run) if run is not None else None
    if queued_id is None:
        await host._finish(update, TEXT_QUEUE_ALREADY, TEXT_QUEUE_ALREADY)
        return
    position = await _position(host, queued_id)
    text = (
        TEXT_DEAD_RETRIED.format(position=position)
        if position
        else TEXT_DEAD_RETRIED_PLAIN
    )
    await host._finish(update, ANSWER_DEAD_RETRIED, text)


async def _retried_run(host: _Host, run: AutopilotRun) -> UUID | None:
    """The run now queued for this dead letter, or None when nothing moved."""
    if not is_dead_letter(run.state_reason):
        return None
    deps = ReviveDependencies(
        runs=host._deps.runs,
        clock=host._deps.clock,
        queue=host._deps.queue,
        dead_letters=host._deps.dead_letters,
    )
    return await revive(deps, run, REASON_DEAD_RETRY)


async def _discard(host: _Host, update: WebhookUpdate, run_id: UUID) -> None:
    run = await host._deps.runs.get(run_id)
    if run is None or not await _discarded(host, run):
        await host._finish(update, TEXT_QUEUE_ALREADY, TEXT_QUEUE_ALREADY)
        return
    await host._finish(update, ANSWER_DEAD_DISCARDED, TEXT_DEAD_DISCARDED)


async def _discarded(host: _Host, run: AutopilotRun) -> bool:
    if not is_dead_letter(run.state_reason):
        return False
    if run.state is AutopilotRunState.ESCALATED:
        return await host._deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=AutopilotRunState.ESCALATED,
                new=AutopilotRunState.REJECTED,
                reason=REASON_DEAD_DISCARD,
            )
        )
    dead_letters = host._deps.dead_letters
    if run.state is not AutopilotRunState.FAILED or dead_letters is None:
        return False
    return await dead_letters.discard_failed(run.run_id)


async def _generate_now(host: _Host, update: WebhookUpdate, candidate_id: UUID) -> None:
    backlog = host._deps.backlog
    run_id = uuid4()
    theme = (
        await backlog.generate_now(
            GenerateNowCommand(
                candidate_id=candidate_id,
                run_id=run_id,
                created_at=host._deps.clock.now(),
            )
        )
        if backlog is not None
        else None
    )
    if theme is None:
        await host._answer(update, TEXT_QUEUE_ALREADY)
        return
    position = await _position(host, run_id)
    await host._answer(update, ANSWER_GENERATED_NOW)
    text = (
        TEXT_GENERATED_NOW.format(title=theme.title, position=position)
        if position
        else TEXT_GENERATED_NOW_PLAIN.format(title=theme.title)
    )
    await host._tell(update, text)


__all__ = ["QueueOwnerActions"]
