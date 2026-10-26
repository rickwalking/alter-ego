"""Owner queue buttons on the webhook: position, approve-all, dead letters, generate now.

Feature: backend/tests/features/telegram_queue_flow_ae0523.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from uuid import UUID, uuid4

import pytest

from rag_backend.modules.autopilot.application.owner_actions import (
    OwnerActionDeps,
    OwnerActionService,
)
from rag_backend.modules.autopilot.application.run_revive import (
    ReviveDependencies,
    revive,
)
from rag_backend.modules.autopilot.domain.backlog import (
    BacklogChange,
    BacklogTheme,
    BacklogWindow,
    GenerateNowCommand,
)
from rag_backend.modules.autopilot.domain.dead_letter import RetryFailedCommand
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    ThesisConfirmCommand,
    TopicCandidate,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.notice_log import NoticeLog
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.queue_position import QueueSnapshot
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.queue_constants import (
    CALLBACK_APPROVE_ALL,
    CALLBACK_GENERATE_NOW_PREFIX,
    REASON_DEAD_LETTER_PREFIX,
    REASON_DEAD_RETRY,
    TEXT_APPROVED_NONE,
    TEXT_QUEUE_ALREADY,
    THESIS_BATCH_NOTICE_KEY,
)
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_owner_actions import (
    _Claims,
    _Clock,
    _Editorial,
    _Messenger,
    _Pending,
    _Release,
    _tap,
)

_OWNER = "42"
_S = AutopilotRunState
_DEAD = f"{REASON_DEAD_LETTER_PREFIX}phase_budget_exhausted"
_THESIS = "Quem decide o que construir ainda é o dev."


def _run(state: AutopilotRunState, reason: str | None = None) -> AutopilotRun:
    """A run; a waiting thesis is one the "Aprovar todas" summary listed."""
    listed = (THESIS_BATCH_NOTICE_KEY,) if state is _S.AWAITING_THESIS else ()
    return AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=uuid4(),
        carousel_project_id=None,
        state=state,
        state_reason=reason,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
        notice_log=NoticeLog(statuses=listed),
    )


def _topic(candidate_id: UUID, title: str, draft: str | None) -> TopicCandidate:
    return TopicCandidate(
        candidate_id=candidate_id,
        title=title,
        angle="a",
        why_viral="w",
        audience="developers",
        niche="AI",
        brief="b",
        sources=("https://example.com/a",),
        score=80,
        signal_hash=title,
        status="accepted",
        content_mode="pov",
        thesis_draft=draft,
    )


@dataclass
class _Runs:
    runs: dict[UUID, AutopilotRun]
    confirms: list[ThesisConfirmCommand] = field(default_factory=list)

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        return self.runs.get(run_id)

    async def transition(self, command: TransitionCommand) -> bool:
        run = self.runs.get(command.run_id)
        if run is None or run.state is not command.expected:
            return False
        self.runs[run.run_id] = replace(
            run, state=command.new, state_reason=command.reason
        )
        return True

    async def confirm_thesis(self, command: ThesisConfirmCommand) -> bool:
        run = self.runs.get(command.run_id)
        if run is None or run.state is not _S.AWAITING_THESIS:
            return False
        self.confirms.append(command)
        self.runs[run.run_id] = replace(run, state=_S.QUEUED, pov_thesis=command.thesis)
        return True

    async def list_by_state(self, query: RunListQuery) -> list[AutopilotRun]:
        return [run for run in self.runs.values() if run.state is query.state][
            : query.limit
        ]


@dataclass
class _Topics:
    topics: dict[UUID, TopicCandidate] = field(default_factory=dict)

    async def add_topic(self, candidate: TopicCandidate) -> None:
        self.topics[candidate.candidate_id] = candidate

    async def get_topic(self, candidate_id: UUID) -> TopicCandidate | None:
        return self.topics.get(candidate_id)


@dataclass
class _Queue:
    """The queue order is derived from the runs: queued/generating, oldest first."""

    runs: _Runs
    ahead: tuple[str | None, ...] = ()
    extra: list[UUID] = field(default_factory=list)
    requeued: list[UUID] = field(default_factory=list)
    dead: _DeadLetters | None = None

    async def snapshot(self) -> QueueSnapshot:
        driven = [
            str(run.run_id)
            for run in self.runs.runs.values()
            if run.state in (_S.QUEUED, _S.GENERATING)
        ]
        waiting = (*driven, *(str(run_id) for run_id in self.extra))
        return QueueSnapshot(ahead=self.ahead, waiting=waiting, drive_minutes=(20.0,))

    async def requeue_dead_letter(self, run_id: UUID) -> bool:
        self.requeued.append(run_id)
        return True

    async def reprocess_autopilot(self, run_id: UUID, actor_id: str) -> UUID | None:
        del actor_id
        run = self.runs.runs.get(run_id)
        if run is None:
            return None
        deps = ReviveDependencies(
            runs=self.runs, clock=_Clock(), queue=self, dead_letters=self.dead
        )
        return await revive(deps, run, REASON_DEAD_RETRY)

    async def deliver_notifications(self) -> None:
        return None

    def discard_notifications(self) -> None:
        return None


@dataclass
class _Backlog:
    themes: dict[UUID, BacklogTheme] = field(default_factory=dict)
    generated: list[GenerateNowCommand] = field(default_factory=list)
    queue: _Queue | None = None

    async def waiting(self, window: BacklogWindow) -> list[BacklogTheme]:
        del window
        return list(self.themes.values())

    async def change(self, change: BacklogChange) -> tuple[UUID, ...]:
        del change
        return ()

    async def unannounced(self) -> list[BacklogTheme]:
        return []

    async def generate_now(self, command: GenerateNowCommand) -> BacklogTheme | None:
        theme = self.themes.pop(command.candidate_id, None)
        if theme is None:
            return None
        self.generated.append(command)
        if self.queue is not None:
            self.queue.extra.append(command.run_id)
        return theme


@dataclass
class _DeadLetters:
    runs: _Runs
    queue: _Queue
    retried: list[RetryFailedCommand] = field(default_factory=list)
    discarded: list[UUID] = field(default_factory=list)

    async def retry_failed(self, command: RetryFailedCommand) -> bool:
        run = self.runs.runs[command.run_id]
        if not (run.state_reason or "").startswith(REASON_DEAD_LETTER_PREFIX):
            return False
        self.runs.runs[run.run_id] = replace(run, state_reason="owner_queue_retry")
        self.retried.append(command)
        self.queue.extra.append(command.new_run_id)
        return True

    async def discard_failed(self, run_id: UUID) -> bool:
        run = self.runs.runs[run_id]
        if not (run.state_reason or "").startswith(REASON_DEAD_LETTER_PREFIX):
            return False
        self.runs.runs[run_id] = replace(run, state_reason="owner_queue_discard")
        self.discarded.append(run_id)
        return True


@dataclass
class _World:
    runs: _Runs
    topics: _Topics
    queue: _Queue
    backlog: _Backlog
    dead: _DeadLetters
    messenger: _Messenger
    service: OwnerActionService


def _world(*runs: AutopilotRun, ahead: tuple[str | None, ...] = ()) -> _World:
    repo = _Runs(runs={run.run_id: run for run in runs})
    topics = _Topics()
    queue = _Queue(runs=repo, ahead=ahead)
    backlog = _Backlog(queue=queue)
    dead = _DeadLetters(runs=repo, queue=queue)
    queue.dead = dead
    messenger = _Messenger()
    service = OwnerActionService(
        OwnerActionDeps(
            runs=repo,
            updates=_Claims(),
            pending=_Pending(),
            editorial=_Editorial(),
            release=_Release(),
            messenger=messenger,
            recovery=_Recovery(runs=repo),
            clock=_Clock(),
            owner_chat_id=_OWNER,
            owner_user_id="owner-user",
            topics=topics,
            queue=queue,
            backlog=backlog,
            dead_letters=dead,
        )
    )
    return _World(
        runs=repo,
        topics=topics,
        queue=queue,
        backlog=backlog,
        dead=dead,
        messenger=messenger,
        service=service,
    )


def _with_draft(
    world: _World, run: AutopilotRun, title: str, draft: str | None
) -> None:
    world.topics.topics[run.topic_candidate_id] = _topic(
        run.topic_candidate_id, title, draft
    )


async def _handle(world: _World, update: WebhookUpdate) -> None:
    await world.service.handle(update)
    await world.service.deliver()


def _said(world: _World) -> list[str]:
    return [e.text for e in world.messenger.edits] + [
        t.text for t in world.messenger.texts
    ]


@pytest.mark.asyncio
async def test_confirm_shows_the_queue_position_and_start() -> None:
    """Scenario: Confirmar shows the queue position and the estimated start"""
    run = _run(_S.AWAITING_THESIS)
    world = _world(run, ahead=("other-run",))
    _with_draft(world, run, "Agents", _THESIS)
    await _handle(world, _tap(1, f"ap:thok:{run.run_id}"))
    text = _said(world)[-1]
    assert _THESIS in text
    assert "Na fila: posição 2 de 2" in text
    assert "início estimado" in text


@pytest.mark.asyncio
async def test_approve_all_confirms_every_waiting_thesis_in_order() -> None:
    """Scenario: "Aprovar todas" confirms every waiting thesis in FIFO order"""
    runs = [_run(_S.AWAITING_THESIS) for _ in range(3)]
    world = _world(*runs)
    for index, run in enumerate(runs):
        _with_draft(world, run, f"T{index}", f"Tese número {index}")
    await _handle(world, _tap(1, CALLBACK_APPROVE_ALL))
    assert all(world.runs.runs[run.run_id].state is _S.QUEUED for run in runs)
    assert [c.run_id for c in world.runs.confirms] == [run.run_id for run in runs]
    summary = _said(world)[-1]
    assert summary.startswith("✅ 3 teses confirmadas")
    for index in range(3):
        assert f"«Tese número {index}» — posição {index + 1} de 3" in summary


@pytest.mark.asyncio
async def test_approve_all_skips_a_thesis_without_a_draft() -> None:
    """Scenario: "Aprovar todas" skips a thesis without a draft"""
    with_draft = _run(_S.AWAITING_THESIS)
    no_draft = _run(_S.AWAITING_THESIS)
    world = _world(with_draft, no_draft)
    _with_draft(world, with_draft, "Ready", _THESIS)
    _with_draft(world, no_draft, "Needs words", None)
    await _handle(world, _tap(1, CALLBACK_APPROVE_ALL))
    assert world.runs.runs[with_draft.run_id].state is _S.QUEUED
    assert world.runs.runs[no_draft.run_id].state is _S.AWAITING_THESIS
    assert "Sem tese, confirme pelo Editar: Needs words" in _said(world)[-1]


@pytest.mark.asyncio
async def test_approve_all_confirms_only_the_listed_theses() -> None:
    """Scenario: "Aprovar todas" confirms only the theses the summary listed"""
    listed = _run(_S.AWAITING_THESIS)
    late = replace(_run(_S.AWAITING_THESIS), notice_log=NoticeLog())
    world = _world(listed, late)
    _with_draft(world, listed, "Listed", _THESIS)
    _with_draft(world, late, "Late", _THESIS)
    await _handle(world, _tap(1, CALLBACK_APPROVE_ALL))
    assert world.runs.runs[listed.run_id].state is _S.QUEUED
    assert world.runs.runs[late.run_id].state is _S.AWAITING_THESIS


@pytest.mark.asyncio
async def test_approve_all_twice_confirms_nothing_new() -> None:
    """Scenario: "Aprovar todas" twice confirms nothing new"""
    run = _run(_S.AWAITING_THESIS)
    world = _world(run)
    _with_draft(world, run, "Once", _THESIS)
    await _handle(world, _tap(1, CALLBACK_APPROVE_ALL))
    await _handle(world, _tap(2, CALLBACK_APPROVE_ALL))
    assert len(world.runs.confirms) == 1
    assert _said(world)[-1] == TEXT_APPROVED_NONE


@pytest.mark.asyncio
async def test_generate_now_queues_a_backlog_theme_once() -> None:
    """Scenario: "Gerar agora" twice queues one run"""
    world = _world(_run(_S.GENERATING))
    theme = BacklogTheme(
        candidate_id=uuid4(), title="Agentes", created_at=datetime.now()
    )
    world.backlog.themes[theme.candidate_id] = theme
    data = f"{CALLBACK_GENERATE_NOW_PREFIX}{theme.candidate_id}"
    await _handle(world, _tap(1, data))
    await _handle(world, _tap(2, data))
    assert len(world.backlog.generated) == 1
    texts = [t.text for t in world.messenger.texts]
    assert len(texts) == 1
    assert texts[0].startswith("⚡ Gerando agora: «Agentes». Na fila: posição 2 de 2")
    assert world.messenger.answers[-1].text == TEXT_QUEUE_ALREADY
