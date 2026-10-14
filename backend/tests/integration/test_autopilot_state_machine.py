"""Persistence behavior for the autopilot state machine (AE-0350).

Gherkin: tests/features/autopilot_state_machine.feature
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.modules.autopilot import (
    AutopilotBootstrapDeps,
    AutopilotService,
    InvalidAutopilotTransition,
    TransitionCommand,
    bootstrap_module,
)
from rag_backend.modules.autopilot.constants import (
    EVENT_TYPE_READY_FOR_OWNER,
    REASON_START_FAILED,
)
from rag_backend.modules.autopilot.domain.gate import (
    AttachProjectCommand,
    OwnerReadyNotice,
    StartAttemptCommand,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    IntegrationCredential,
    TelegramUpdate,
    TopicCandidate,
)
from rag_backend.modules.autopilot.infrastructure.ready_notifier import (
    OutboxReadyNotifier,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)

_EVENT_TYPE = "content.autopilot.state_changed"
_RUNNER_TICK = "runner tick"
_OWNER_APPROVE = "owner approve"


def _topic() -> TopicCandidate:
    return TopicCandidate(
        candidate_id=uuid4(),
        title="Agents that ship",
        angle="operator view",
        why_viral="three launches in one week",
        audience="builders",
        niche="ai",
        brief="A short brief.",
        sources=("https://example.com/story",),
        score=80,
        signal_hash=uuid4().hex,
        status="new",
    )


def _run(topic_id: UUID, state: AutopilotRunState) -> AutopilotRun:
    return AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=topic_id,
        carousel_project_id=None,
        state=state,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )


def _command(run_id: UUID, expected: AutopilotRunState, new: AutopilotRunState, reason: str) -> TransitionCommand:
    return TransitionCommand(run_id=run_id, expected=expected, new=new, reason=reason)


async def _persist(
    repo: SqlAlchemyAutopilotRepository, state: AutopilotRunState
) -> AutopilotRun:
    topic = _topic()
    await repo.add_topic(topic)
    run = _run(topic.candidate_id, state)
    await repo.add(run)
    return run


async def _events(db: AsyncSession, run_id: UUID) -> list[EventOutboxModel]:
    result = await db.execute(
        select(EventOutboxModel).where(EventOutboxModel.aggregate_id == str(run_id))
    )
    return [row for row in result.scalars().all() if row.event_type == _EVENT_TYPE]


def _wired(db: AsyncSession) -> tuple[SqlAlchemyAutopilotRepository, AutopilotService]:
    repo = SqlAlchemyAutopilotRepository(db)
    service = bootstrap_module(AutopilotBootstrapDeps(session=db))
    return repo, service


# Scenario: Allowed transition persists and emits an event
@pytest.mark.asyncio
async def test_allowed_transition_persists_and_emits(db_session: AsyncSession) -> None:
    """Given queued, when it moves to generating, then state and one outbox row."""
    repo, service = _wired(db_session)
    run = await _persist(repo, AutopilotRunState.QUEUED)

    changed = await service.transition(
        _command(run.run_id, AutopilotRunState.QUEUED, AutopilotRunState.GENERATING, _RUNNER_TICK)
    )

    assert changed is True
    view = await service.get_run(run.run_id)
    assert view is not None
    assert view.state == "generating"
    assert view.state_reason == _RUNNER_TICK
    events = await _events(db_session, run.run_id)
    assert len(events) == 1
    assert events[0].payload == {
        "previous_state": "queued",
        "state": "generating",
        "reason": _RUNNER_TICK,
    }


# Scenario: Concurrent transition loses the compare-and-set
@pytest.mark.asyncio
async def test_stale_compare_and_set_writes_nothing_more(db_session: AsyncSession) -> None:
    """A second actor with a stale expected state loses and adds no outbox row."""
    repo, service = _wired(db_session)
    run = await _persist(repo, AutopilotRunState.AWAITING_OWNER)
    first = await service.transition(
        _command(
            run.run_id,
            AutopilotRunState.AWAITING_OWNER,
            AutopilotRunState.PUBLISHING,
            _OWNER_APPROVE,
        )
    )
    assert first is True
    before = await _events(db_session, run.run_id)

    second = await service.transition(
        _command(
            run.run_id,
            AutopilotRunState.AWAITING_OWNER,
            AutopilotRunState.PUBLISHING,
            _OWNER_APPROVE,
        )
    )

    assert second is False
    assert await _events(db_session, run.run_id) == before
    view = await service.get_run(run.run_id)
    assert view is not None
    assert view.state == "publishing"


# Scenario: Illegal transition is rejected
@pytest.mark.asyncio
async def test_illegal_transition_raises_and_does_not_emit(db_session: AsyncSession) -> None:
    """Published cannot move to generating, and no outbox row is written."""
    repo, service = _wired(db_session)
    run = await _persist(repo, AutopilotRunState.PUBLISHED)

    with pytest.raises(InvalidAutopilotTransition):
        await service.transition(
            _command(
                run.run_id,
                AutopilotRunState.PUBLISHED,
                AutopilotRunState.GENERATING,
                "rewind",
            )
        )
    view = await service.get_run(run.run_id)
    assert view is not None
    assert view.state == "published"
    assert await _events(db_session, run.run_id) == []


# Scenario: Missing run does not emit an event
@pytest.mark.asyncio
async def test_missing_run_returns_false_without_event(db_session: AsyncSession) -> None:
    """A legal pair against an unknown id changes nothing."""
    _repo, service = _wired(db_session)
    missing = uuid4()

    changed = await service.transition(
        _command(missing, AutopilotRunState.QUEUED, AutopilotRunState.GENERATING, _RUNNER_TICK)
    )

    assert changed is False
    assert await service.get_run(missing) is None
    assert await _events(db_session, missing) == []


# Scenario: Allowed transition persists and emits an event (rollback half)
@pytest.mark.asyncio
async def test_rollback_discards_the_outbox_row(db_session: AsyncSession) -> None:
    """The outbox row shares the state transaction: rollback drops both."""
    repo, service = _wired(db_session)
    run = await _persist(repo, AutopilotRunState.QUEUED)
    await service.transition(
        _command(run.run_id, AutopilotRunState.QUEUED, AutopilotRunState.GENERATING, _RUNNER_TICK)
    )
    assert len(await _events(db_session, run.run_id)) == 1

    await db_session.rollback()

    assert await _events(db_session, run.run_id) == []
    assert await service.get_run(run.run_id) is None


@pytest.mark.asyncio
async def test_topic_credential_and_telegram_round_trip(db_session: AsyncSession) -> None:
    """The three supporting tables persist and read back."""
    repo, _service = _wired(db_session)
    topic = _topic()
    await repo.add_topic(topic)
    stored_topic = await repo.get_topic(topic.candidate_id)
    assert stored_topic == topic
    assert await repo.get_topic(uuid4()) is None

    moment = datetime(2026, 10, 13, tzinfo=UTC)
    credential = IntegrationCredential(
        provider="instagram",
        encrypted_token="enc:v1:not-a-real-token",
        expires_at=moment,
        refreshed_at=None,
    )
    await repo.add_credential(credential)
    stored_credential = await repo.get_credential("instagram")
    assert stored_credential is not None
    assert stored_credential.provider == credential.provider
    assert stored_credential.encrypted_token == credential.encrypted_token
    assert stored_credential.refreshed_at is None
    assert stored_credential.expires_at is not None
    assert await repo.get_credential("missing") is None

    update = TelegramUpdate(update_id=2**40, received_at=moment)
    await repo.add_telegram_update(update)
    assert await repo.has_telegram_update(update.update_id) is True
    assert await repo.has_telegram_update(update.update_id + 1) is False


@pytest.mark.asyncio
async def test_queued_start_failure_persists(db_session: AsyncSession) -> None:
    """A start outage stays queued until the third failure moves it to failed."""
    repo, service = _wired(db_session)
    run = await _persist(repo, AutopilotRunState.QUEUED)
    attached = await repo.attach_project(
        AttachProjectCommand(run_id=run.run_id, project_id="carousel-1")
    )
    assert attached is True
    again = await repo.attach_project(
        AttachProjectCommand(run_id=run.run_id, project_id="carousel-2")
    )
    assert again is False
    noted = await repo.note_start_attempt(
        StartAttemptCommand(run_id=run.run_id, attempts=3, reason=REASON_START_FAILED)
    )
    assert noted is True
    changed = await service.transition(
        _command(run.run_id, AutopilotRunState.QUEUED, AutopilotRunState.FAILED, REASON_START_FAILED)
    )
    assert changed is True
    view = await service.get_run(run.run_id)
    stored = await repo.get(run.run_id)
    assert view is not None
    assert stored is not None
    assert view.state == "failed"
    assert view.state_reason == REASON_START_FAILED
    assert stored.start_attempts == 3
    assert stored.carousel_project_id == "carousel-1"


@pytest.mark.asyncio
async def test_ready_for_owner_is_one_outbox_row(db_session: AsyncSession) -> None:
    """The runner's notice is the ready_for_owner event, not a Telegram call."""
    run_id = uuid4()
    await OutboxReadyNotifier(db_session).notify_ready(
        OwnerReadyNotice(run_id=run_id, project_id="carousel-1")
    )
    result = await db_session.execute(
        select(EventOutboxModel).where(EventOutboxModel.aggregate_id == str(run_id))
    )
    rows = list(result.scalars().all())
    assert len(rows) == 1
    assert rows[0].event_type == EVENT_TYPE_READY_FOR_OWNER
    assert rows[0].payload == {
        "project_id": "carousel-1",
        "revision": 0,
        "persona_score": None,
        "sources_count": 0,
    }
