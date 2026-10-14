"""Owner Telegram actions (AE-0356).

Gherkin: tests/features/autopilot_owner_actions.feature
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from rag_backend.modules.autopilot.application.owner_actions import (
    OwnerActionDeps,
    OwnerActionService,
)
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.constants import (
    GATE_CONTENT,
    GATE_FINAL_REVIEW,
    GATE_IMAGES,
    PHASE_STATUS_AWAITING,
)
from rag_backend.modules.autopilot.domain.callback_parse import parse_callback
from rag_backend.modules.autopilot.domain.gate import (
    GateSnapshot,
    ImageFact,
    OwnerReadyNotice,
    ResearchSourceFact,
    ResumeCommand,
    ResumeResult,
    ResumeStatus,
)
from rag_backend.modules.autopilot.domain.messages import rework_phase_keyboard
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TelegramUpdate,
    TopicCandidate,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.owner_ports import (
    CallbackAnswer,
    ForceReplyPrompt,
    MessageEdit,
    OwnerText,
    PendingRework,
    ReleaseCommand,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.webhook_update import (
    WebhookUpdate,
    is_owner,
    parse_webhook_body,
    secrets_match,
)
from rag_backend.modules.autopilot.webhook_constants import (
    ANSWER_ALREADY,
    ANSWER_UNKNOWN,
    KIND_CALLBACK,
    KIND_MESSAGE,
    KIND_PHASE,
    TEXT_FORCE_REPLY,
)
from rag_backend.modules.editorial.public import (
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
)

_OWNER = "42"
_STRANGER = "99"
_PROJECT = "11111111-1111-4111-8111-111111111111"
_FEEDBACK = "darker palette, no robots"


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 10, 14, tzinfo=UTC)


@dataclass
class _Runs:
    run: AutopilotRun
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        await asyncio.sleep(0)
        if self.run.run_id != run_id:
            return None
        return self.run

    async def transition(self, command: TransitionCommand) -> bool:
        await asyncio.sleep(0)
        async with self.lock:
            if self.run.run_id != command.run_id:
                return False
            if self.run.state is not command.expected:
                return False
            self.run = replace(
                self.run,
                state=command.new,
                state_reason=command.reason,
            )
            return True

    async def list_by_state(self, query: RunListQuery) -> list[AutopilotRun]:
        if self.run.state is query.state:
            return [self.run]
        return []


@dataclass
class _Claims:
    seen: set[int] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def claim_update(self, update: TelegramUpdate) -> bool:
        async with self.lock:
            if update.update_id in self.seen:
                return False
            self.seen.add(update.update_id)
            return True


@dataclass
class _Pending:
    item: PendingRework | None = None

    async def put(self, pending: PendingRework) -> None:
        self.item = pending

    async def take(self, owner_chat_id: str) -> PendingRework | None:
        if self.item is None or self.item.owner_chat_id != owner_chat_id:
            return None
        item = self.item
        self.item = None
        return item


@dataclass
class _Editorial:
    resumes: list[ResumeCommand] = field(default_factory=list)
    status: ResumeStatus = ResumeStatus.APPLIED

    async def read_gate(self, project_id: str) -> GateSnapshot:
        del project_id
        return _snapshot()

    async def resume(self, command: ResumeCommand) -> ResumeResult:
        await asyncio.sleep(0)
        self.resumes.append(command)
        return ResumeResult(status=self.status)


@dataclass
class _Release:
    ids: list[str] = field(default_factory=list)
    public: bool = False
    ok: bool = True

    async def release(self, command: ReleaseCommand) -> bool:
        if not self.ok:
            return False
        self.ids.append(command.project_id)
        self.public = True
        return True


@dataclass
class _Messenger:
    answers: list[CallbackAnswer] = field(default_factory=list)
    edits: list[MessageEdit] = field(default_factory=list)
    asks: list[ForceReplyPrompt] = field(default_factory=list)
    texts: list[OwnerText] = field(default_factory=list)

    async def answer(self, command: CallbackAnswer) -> None:
        self.answers.append(command)

    async def edit(self, command: MessageEdit) -> None:
        self.edits.append(command)

    async def ask(self, command: ForceReplyPrompt) -> None:
        self.asks.append(command)

    async def tell(self, command: OwnerText) -> None:
        self.texts.append(command)


class _Topics:
    async def add_topic(self, candidate: TopicCandidate) -> None:
        del candidate

    async def get_topic(self, candidate_id: UUID) -> TopicCandidate | None:
        del candidate_id
        return None


@dataclass
class _Notices:
    ready: list[OwnerReadyNotice] = field(default_factory=list)

    async def notify_ready(self, notice: OwnerReadyNotice) -> None:
        self.ready.append(notice)


@dataclass
class _World:
    runs: _Runs
    claims: _Claims
    pending: _Pending
    editorial: _Editorial
    release: _Release
    messenger: _Messenger
    service: OwnerActionService


def test_secret_and_owner_compare_are_exact() -> None:
    """Scenario: Forged request — a wrong or empty secret matches nothing."""
    assert secrets_match("hook-secret", "hook-secret") is True
    assert secrets_match("hook-secret", "other-secret") is False
    assert secrets_match("", "hook-secret") is False
    assert secrets_match("hook-secret", "") is False
    assert is_owner(_OWNER, _OWNER) is True
    assert is_owner(_STRANGER, _OWNER) is False
    assert is_owner(_OWNER, "") is False


def test_parse_callback_maps_text_to_content() -> None:
    """Rework phase tokens are strict. Text becomes the content phase."""
    run_id = uuid4()
    approved = parse_callback(f"ap:approve:{run_id}")
    assert approved is not None
    assert approved.kind == "approve"
    assert approved.run_id == run_id
    images = parse_callback(f"ap:rw:images:{run_id}")
    assert images is not None and images.kind == KIND_PHASE
    assert images.phase == GATE_IMAGES
    text = parse_callback(f"ap:rw:text:{run_id}")
    assert text is not None and text.phase == GATE_CONTENT
    assert parse_callback(f"ap:approve:{run_id} ") is None
    assert parse_callback("ap:approve:not-a-uuid") is None
    assert parse_callback("ap:dance:" + str(run_id)) is None


def test_parse_webhook_ignores_non_updates() -> None:
    assert parse_webhook_body(None) is None
    assert parse_webhook_body({"update_id": True}) is None
    ignored = parse_webhook_body({"update_id": 3, "edited_message": {}})
    assert ignored is not None and ignored.kind == "ignored"
    body = {
        "update_id": 4,
        "callback_query": {
            "id": "cb",
            "from": {"id": 42},
            "data": "ap:reject:" + str(uuid4()),
            "message": {"message_id": 9, "chat": {"id": 42}},
        },
    }
    parsed = parse_webhook_body(body)
    assert parsed is not None
    assert parsed.actor_id == _OWNER
    assert parsed.message_id == 9


def test_rework_keyboard_uses_phase_tokens() -> None:
    run_id = uuid4()
    buttons = [button for row in rework_phase_keyboard(run_id).rows for button in row]
    labels = [button.text for button in buttons]
    assert labels == ["Text", "Design", "Images", "Outline"]
    assert f"ap:rw:text:{run_id}" in buttons[0].callback_data
    assert f"ap:rw:images:{run_id}" in buttons[2].callback_data


# Scenario: Approve publishes once
@pytest.mark.asyncio
async def test_approve_twice_publishes_once() -> None:
    world = _world()
    await world.service.handle(_tap(1, _action("approve", world)))
    await world.service.handle(_tap(2, _action("approve", world)))
    assert len(world.editorial.resumes) == 1
    assert world.editorial.resumes[0].action == REVIEW_ACTION_APPROVE
    assert world.editorial.resumes[0].phase == GATE_FINAL_REVIEW
    assert world.release.ids == [_PROJECT]
    assert world.runs.run.state is AutopilotRunState.PUBLISHING
    assert world.messenger.answers[-1].text == ANSWER_ALREADY


# Scenario: Approve publishes once (concurrent double tap)
@pytest.mark.asyncio
async def test_concurrent_double_approve_publishes_once() -> None:
    world = _world()
    await asyncio.gather(
        world.service.handle(_tap(1, _action("approve", world))),
        world.service.handle(_tap(2, _action("approve", world))),
    )
    assert len(world.editorial.resumes) == 1
    assert len(world.release.ids) == 1
    assert world.runs.run.state is AutopilotRunState.PUBLISHING


# Scenario: Stranger presses a button
@pytest.mark.asyncio
async def test_stranger_does_not_change_the_run() -> None:
    world = _world()
    await world.service.handle(_tap(1, _action("approve", world), actor=_STRANGER))
    assert world.runs.run.state is AutopilotRunState.AWAITING_OWNER
    assert world.editorial.resumes == []
    assert world.release.ids == []
    assert world.messenger.answers == []


# Scenario: Reject
@pytest.mark.asyncio
async def test_reject_keeps_the_carousel_private() -> None:
    world = _world()
    await world.service.handle(_tap(1, _action("reject", world)))
    assert world.runs.run.state is AutopilotRunState.REJECTED
    assert world.release.public is False
    assert world.release.ids == []
    assert world.editorial.resumes == []


# Scenario: Already handled
@pytest.mark.asyncio
async def test_approve_when_not_awaiting_is_already_handled() -> None:
    world = _world()
    world.runs.run = replace(world.runs.run, state=AutopilotRunState.PUBLISHING)
    await world.service.handle(_tap(1, _action("approve", world)))
    assert world.messenger.answers[-1].text == ANSWER_ALREADY
    assert world.runs.run.state is AutopilotRunState.PUBLISHING
    assert world.editorial.resumes == []
    assert world.messenger.edits[-1].keyboard is None


# Scenario: Duplicate delivery
@pytest.mark.asyncio
async def test_same_update_id_does_not_approve_again() -> None:
    world = _world()
    tap = _tap(1, _action("approve", world))
    await world.service.handle(tap)
    await world.service.handle(tap)
    assert len(world.editorial.resumes) == 1
    assert len(world.release.ids) == 1


# Scenario: Unknown action
@pytest.mark.asyncio
async def test_unknown_callback_does_not_change_the_run() -> None:
    world = _world()
    await world.service.handle(_tap(1, "ap:dance:" + str(world.runs.run.run_id)))
    assert world.messenger.answers[-1].text == ANSWER_UNKNOWN
    assert world.runs.run.state is AutopilotRunState.AWAITING_OWNER
    assert world.editorial.resumes == []


# Scenario: Rework with feedback
@pytest.mark.asyncio
async def test_rework_images_revises_and_returns_to_the_owner() -> None:
    world = _world()
    notices = _Notices()
    await world.service.handle(_tap(1, _action("rework", world)))
    assert world.runs.run.state is AutopilotRunState.AWAITING_OWNER
    await world.service.handle(_tap(2, f"ap:rw:images:{world.runs.run.run_id}"))
    assert world.pending.item is not None
    assert world.pending.item.phase == GATE_IMAGES
    assert world.messenger.asks[-1].text == TEXT_FORCE_REPLY
    await world.service.handle(_text(3, _FEEDBACK))
    assert len(world.editorial.resumes) == 1
    revise = world.editorial.resumes[0]
    assert revise.action == REVIEW_ACTION_REVISE
    assert revise.feedback == _FEEDBACK
    assert revise.target_phase == GATE_IMAGES
    assert world.runs.run.state is AutopilotRunState.REWORKING
    runner = AutopilotRunner(
        RunnerDependencies(
            runs=world.runs,
            topics=_Topics(),
            editorial=world.editorial,
            notices=notices,
            owner_user_id="owner",
            notifier_configured=True,
        )
    )
    assert await runner.tick() == 1
    assert world.runs.run.state is AutopilotRunState.AWAITING_OWNER
    assert len(notices.ready) == 1


# Scenario: Revision cap escalates
@pytest.mark.asyncio
async def test_revision_cap_escalates() -> None:
    world = _world()
    world.editorial.status = ResumeStatus.REVISION_CAP
    await world.service.handle(_tap(1, _action("rework", world)))
    await world.service.handle(_tap(2, f"ap:rw:text:{world.runs.run.run_id}"))
    await world.service.handle(_text(3, _FEEDBACK))
    assert world.editorial.resumes[0].target_phase == GATE_CONTENT
    assert world.runs.run.state is AutopilotRunState.ESCALATED


# Scenario: Retry enqueues once
@pytest.mark.asyncio
async def test_retry_enqueues_once() -> None:
    world = _world()
    world.runs.run = replace(world.runs.run, state=AutopilotRunState.PUBLISH_FAILED)
    await world.service.handle(_tap(1, _action("retry", world)))
    await world.service.handle(_tap(2, _action("retry", world)))
    assert world.runs.run.state is AutopilotRunState.PUBLISHING
    assert world.editorial.resumes == []
    assert world.release.ids == []
    assert world.messenger.answers[-1].text == ANSWER_ALREADY


@pytest.mark.asyncio
async def test_blank_text_keeps_the_pending_phase() -> None:
    world = _world()
    await world.service.handle(_tap(1, _action("rework", world)))
    await world.service.handle(_tap(2, f"ap:rw:images:{world.runs.run.run_id}"))
    await world.service.handle(_text(3, "   "))
    assert world.pending.item is not None
    assert world.editorial.resumes == []
    assert world.runs.run.state is AutopilotRunState.AWAITING_OWNER


@pytest.mark.asyncio
async def test_rework_after_reject_is_already_handled() -> None:
    world = _world()
    await world.service.handle(_tap(1, _action("reject", world)))
    await world.service.handle(_tap(2, _action("rework", world)))
    assert world.messenger.answers[-1].text == ANSWER_ALREADY
    assert world.runs.run.state is AutopilotRunState.REJECTED


@pytest.mark.asyncio
async def test_failed_release_does_not_stay_publishing() -> None:
    world = _world()
    world.release.ok = False
    await world.service.handle(_tap(1, _action("approve", world)))
    assert world.runs.run.state is AutopilotRunState.PUBLISH_FAILED
    assert world.release.public is False


def _world() -> _World:
    run = AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=uuid4(),
        carousel_project_id=_PROJECT,
        state=AutopilotRunState.AWAITING_OWNER,
        state_reason=None,
        attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )
    runs = _Runs(run=run)
    claims = _Claims()
    pending = _Pending()
    editorial = _Editorial()
    release = _Release()
    messenger = _Messenger()
    service = OwnerActionService(
        OwnerActionDeps(
            runs=runs,
            updates=claims,
            pending=pending,
            editorial=editorial,
            release=release,
            messenger=messenger,
            clock=_Clock(),
            owner_chat_id=_OWNER,
        )
    )
    return _World(
        runs=runs,
        claims=claims,
        pending=pending,
        editorial=editorial,
        release=release,
        messenger=messenger,
        service=service,
    )


def _action(name: str, world: _World) -> str:
    return f"ap:{name}:{world.runs.run.run_id}"


def _tap(update_id: int, data: str, actor: str = _OWNER) -> WebhookUpdate:
    return WebhookUpdate(
        update_id=update_id,
        kind=KIND_CALLBACK,
        actor_id=actor,
        chat_id=actor,
        callback_id=f"cb-{update_id}",
        data=data,
        message_id=9,
    )


def _text(update_id: int, text: str) -> WebhookUpdate:
    return WebhookUpdate(
        update_id=update_id,
        kind=KIND_MESSAGE,
        actor_id=_OWNER,
        chat_id=_OWNER,
        text=text,
    )


def _snapshot() -> GateSnapshot:
    source = ResearchSourceFact(content="body", summary="", key_points=())
    image = ImageFact(present=True, is_jpeg=True, width=1080, height=1350)
    return GateSnapshot(
        phase=GATE_FINAL_REVIEW,
        phase_status=PHASE_STATUS_AWAITING,
        lock_version=4,
        sources=(source, source, source),
        outline_count=6,
        slides_total=6,
        persona_score=80.0,
        forbidden_hits=(),
        presentation_blockers=(),
        images=(image,),
        revisions_used=0,
        stale=False,
    )
