"""Owner thesis buttons and the edited-thesis reply on the webhook.

Gherkin: tests/features/autopilot_pov_thesis.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from rag_backend.modules.autopilot.application.owner_actions import (
    OwnerActionDeps,
    OwnerActionService,
)
from rag_backend.modules.autopilot.application.run_recovery import (
    RecoveryDependencies,
    RunRecovery,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    ThesisConfirmCommand,
    TopicCandidate,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.pov_constants import (
    REASON_THESIS_EXPIRED,
    REASON_THESIS_REQUESTED,
    TEXT_THESIS_ALREADY,
    TEXT_THESIS_DISCARDED,
    TEXT_THESIS_EDIT,
    TEXT_THESIS_TOO_LONG,
    THESIS_PENDING_PHASE,
)
from tests.unit.modules.autopilot.test_autopilot_runner import (
    _Editorial as _RunnerEditorial,
)
from tests.unit.modules.autopilot.test_autopilot_runner import (
    _Notices as _RunnerNotices,
)
from tests.unit.modules.autopilot.test_autopilot_runner import (
    _Recovery,
    _runner,
)
from tests.unit.modules.autopilot.test_autopilot_runner import _Runs as _RunnerRuns
from tests.unit.modules.autopilot.test_owner_actions import (
    _Claims,
    _Clock,
    _Editorial,
    _Messenger,
    _Pending,
    _Release,
    _tap,
    _text,
)

_OWNER = "42"
_URL = "https://x.com/openai/status/2010000000000000001"
_DRAFT = "A IA escreve código; decidir o que construir continua sendo do dev."
_MINE = "Quem decide o que construir ainda é o dev."
_S = AutopilotRunState


@dataclass
class _ThesisRuns:
    run: AutopilotRun
    confirms: list[ThesisConfirmCommand] = field(default_factory=list)

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        return self.run if self.run.run_id == run_id else None

    async def transition(self, command: TransitionCommand) -> bool:
        if self.run.state is not command.expected:
            return False
        self.run = replace(self.run, state=command.new, state_reason=command.reason)
        return True

    async def confirm_thesis(self, command: ThesisConfirmCommand) -> bool:
        if self.run.state is not _S.AWAITING_THESIS:
            return False
        self.confirms.append(command)
        self.run = replace(self.run, state=_S.QUEUED, pov_thesis=command.thesis)
        return True


@dataclass
class _DraftTopics:
    topic: TopicCandidate | None

    async def add_topic(self, candidate: TopicCandidate) -> None:
        del candidate

    async def get_topic(self, candidate_id: UUID) -> TopicCandidate | None:
        del candidate_id
        return self.topic


def _topic(draft: str | None) -> TopicCandidate:
    return TopicCandidate(
        candidate_id=uuid4(),
        title="Agents that ship code",
        angle="a",
        why_viral="w",
        audience="developers",
        niche="AI agents",
        brief="b",
        sources=(_URL,),
        score=80,
        signal_hash="h",
        status="accepted",
        content_mode="pov",
        thesis_draft=draft,
    )


@dataclass
class _World:
    runs: _ThesisRuns
    pending: _Pending
    messenger: _Messenger
    service: OwnerActionService


def _world(
    state: AutopilotRunState = _S.AWAITING_THESIS, draft: str | None = _DRAFT
) -> _World:
    run = AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=uuid4(),
        carousel_project_id=None,
        state=state,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )
    runs = _ThesisRuns(run=run)
    pending = _Pending()
    messenger = _Messenger()
    service = OwnerActionService(
        OwnerActionDeps(
            runs=runs,
            updates=_Claims(),
            pending=pending,
            editorial=_Editorial(),
            release=_Release(),
            messenger=messenger,
            recovery=_Recovery(runs=runs),
            clock=_Clock(),
            owner_chat_id=_OWNER,
            topics=_DraftTopics(topic=_topic(draft)),
        )
    )
    return _World(runs=runs, pending=pending, messenger=messenger, service=service)


def _data(kind: str, world: _World) -> str:
    return f"ap:{kind}:{world.runs.run.run_id}"


async def _handle(world: _World, update: WebhookUpdate) -> None:
    await world.service.handle(update)
    await world.service.deliver()


def _said(world: _World) -> list[str]:
    edits = [e.text for e in world.messenger.edits]
    return edits + [t.text for t in world.messenger.texts]


@pytest.mark.unit
class TestThesisButtons:
    # Scenario: Owner confirms the draft thesis
    # Scenario: Double tap confirms once
    @pytest.mark.asyncio
    async def test_confirm_requeues_once(self) -> None:
        world = _world()
        await _handle(world, _tap(1, _data("thok", world)))
        await _handle(world, _tap(2, _data("thok", world)))
        assert world.runs.run.state is _S.QUEUED
        assert world.runs.run.pov_thesis == _DRAFT
        assert len(world.runs.confirms) == 1
        assert any(_DRAFT in text for text in _said(world))
        assert TEXT_THESIS_ALREADY in _said(world)

    # Scenario: Owner discards
    @pytest.mark.asyncio
    async def test_discard_rejects(self) -> None:
        world = _world()
        await _handle(world, _tap(1, _data("thno", world)))
        assert world.runs.run.state is _S.REJECTED
        assert world.runs.confirms == []
        assert TEXT_THESIS_DISCARDED in _said(world)

    # Scenario: A non-owner taps a thesis button
    @pytest.mark.asyncio
    async def test_stranger_changes_nothing(self) -> None:
        world = _world()
        await _handle(world, _tap(1, _data("thok", world), actor="99"))
        assert world.runs.run.state is _S.AWAITING_THESIS
        assert world.runs.confirms == []

    @pytest.mark.asyncio
    async def test_resolved_run_answers_already(self) -> None:
        world = _world(state=_S.QUEUED)
        await _handle(world, _tap(1, _data("thno", world)))
        assert world.runs.run.state is _S.QUEUED
        assert TEXT_THESIS_ALREADY in _said(world)

    @pytest.mark.asyncio
    async def test_confirm_without_draft_asks_for_one(self) -> None:
        world = _world(draft=None)
        await _handle(world, _tap(1, _data("thok", world)))
        assert world.runs.run.state is _S.AWAITING_THESIS
        assert [a.text for a in world.messenger.asks] == [TEXT_THESIS_EDIT]


@pytest.mark.unit
class TestEditedThesis:
    # Scenario: Owner edits the thesis
    @pytest.mark.asyncio
    async def test_edit_then_reply_confirms_the_owners_text(self) -> None:
        world = _world()
        await _handle(world, _tap(1, _data("thed", world)))
        assert world.pending.item is not None
        assert world.pending.item.phase == THESIS_PENDING_PHASE
        await _handle(world, _text(2, f"  {_MINE}  "))
        assert world.runs.run.state is _S.QUEUED
        assert world.runs.run.pov_thesis == _MINE
        assert world.pending.item is None

    # Scenario: Edited thesis too long
    @pytest.mark.asyncio
    async def test_too_long_reply_keeps_waiting(self) -> None:
        world = _world()
        await _handle(world, _tap(1, _data("thed", world)))
        await _handle(world, _text(2, "x" * 281))
        assert world.runs.run.state is _S.AWAITING_THESIS
        assert world.pending.item is not None
        assert TEXT_THESIS_TOO_LONG in _said(world)

    @pytest.mark.asyncio
    async def test_reply_after_discard_is_already(self) -> None:
        world = _world()
        await _handle(world, _tap(1, _data("thed", world)))
        world.runs.run = replace(world.runs.run, state=_S.REJECTED)
        await _handle(world, _text(2, _MINE))
        assert world.runs.confirms == []
        assert TEXT_THESIS_ALREADY in _said(world)


def _queued_pov(thesis: str | None) -> _RunnerRuns:
    world = _world(state=_S.QUEUED)
    run = replace(world.runs.run, pov_thesis=thesis)
    return _RunnerRuns(run=run, topic=_topic(_DRAFT))


@pytest.mark.unit
class TestRunnerThesisGate:
    # Scenario: A POV run waits for the thesis
    @pytest.mark.asyncio
    async def test_unconfirmed_pov_run_waits(self) -> None:
        runs = _queued_pov(None)
        editorial = _RunnerEditorial()
        await _runner(runs, editorial, _RunnerNotices()).tick()
        assert runs.run.state is _S.AWAITING_THESIS
        assert runs.run.state_reason == REASON_THESIS_REQUESTED
        assert editorial.starts == 0

    # Scenario: A confirmed POV run starts generating
    @pytest.mark.asyncio
    async def test_confirmed_pov_run_starts(self) -> None:
        runs = _queued_pov(_MINE)
        editorial = _RunnerEditorial()
        await _runner(runs, editorial, _RunnerNotices()).tick()
        assert runs.run.state is _S.GENERATING
        assert editorial.starts == 1


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 10, 20, tzinfo=UTC)


@pytest.mark.unit
class TestThesisExpiry:
    # Scenario: Unanswered thesis expires
    @pytest.mark.parametrize(("age_hours", "expired"), [(73, True), (71, False)])
    @pytest.mark.asyncio
    async def test_expiry(self, age_hours: int, expired: bool) -> None:
        runs = _queued_pov(None)
        updated = _FixedClock().now() - timedelta(hours=age_hours)
        runs.run = replace(runs.run, state=_S.AWAITING_THESIS, updated_at=updated)
        recovery = RunRecovery(
            RecoveryDependencies(
                runs=runs,
                editorial=_RunnerEditorial(),
                notices=_RunnerNotices(),
                recovery=_Recovery(runs=runs),
                clock=_FixedClock(),
                notifier_configured=True,
            )
        )
        await recovery.sweep()
        assert (runs.run.state is _S.EXPIRED) is expired
        if expired:
            assert runs.run.state_reason == REASON_THESIS_EXPIRED
