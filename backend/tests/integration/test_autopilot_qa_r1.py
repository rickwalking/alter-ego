"""Persistence-backed QA round 1 fixes (AE-0348): B2, B3, H1, cursor, intake.

Gherkin:
  tests/features/autopilot_instagram_publish.feature
  tests/features/autopilot_telegram_notify.feature
  tests/features/autopilot_topic_intake.feature
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.modules.autopilot import AutopilotBootstrapDeps, bootstrap_module
from rag_backend.modules.autopilot.api.schemas import ObservedXPost, TopicProposal
from rag_backend.modules.autopilot.application.manual_publish import (
    ManualInstagramPublish,
)
from rag_backend.modules.autopilot.application.publish_job import (
    InstagramPublishJob,
    PublishJobDependencies,
)
from rag_backend.modules.autopilot.application.topic_intake import (
    TopicIntakeCommand,
    TopicIntakeDependencies,
    TopicIntakeService,
)
from rag_backend.modules.autopilot.constants import (
    EVENT_TYPE_READY_FOR_OWNER,
    REASON_DUPLICATE_TOPIC,
    URL_MAX_CHARS,
)
from rag_backend.modules.autopilot.domain.exceptions import ManualPublishRefusedError
from rag_backend.modules.autopilot.domain.gate import StartAttemptCommand
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.ports import HashLookup, RecordServedUrls
from rag_backend.modules.autopilot.domain.publish import (
    DueFacts,
    ManualPublishCommand,
    is_publish_due,
)
from rag_backend.modules.autopilot.domain.publish_claims import RunClaim
from rag_backend.modules.autopilot.infrastructure.intake_store import (
    SqlAlchemyTopicIntakeStore,
)
from rag_backend.modules.autopilot.infrastructure.models import TopicCandidateModel
from rag_backend.modules.autopilot.infrastructure.notice_source import (
    SqlAutopilotEventSource,
)
from rag_backend.modules.autopilot.infrastructure.publish_claims import (
    SqlPublishClaims,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.recovery_constants import (
    ERR_AUTOPILOT_RUN_ACTIVE,
    ERR_PUBLISH_IN_PROGRESS,
)
from rag_backend.modules.autopilot.webhook_constants import REASON_OWNER_RETRY
from tests.integration.autopilot_topic_support import _URL_A, _Clock, _proposal
from tests.integration.test_autopilot_state_machine import _topic
from tests.unit.modules.autopilot.test_instagram_publish_job import (
    _SEVEN,
    _Gateway,
    _Notifier,
    _snapshot,
    _Source,
)

_NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


class _FixedClock:
    def now(self) -> datetime:
        return _NOW


async def _carousel(db: AsyncSession) -> str:
    project_id = str(uuid4())
    db.add(CarouselProjectModel(id=project_id, topic="T", audience="A", niche="N"))
    await db.flush()
    return project_id


async def _run_in(
    db: AsyncSession,
    state: AutopilotRunState,
    publish_attempts: int = 0,
) -> tuple[SqlAlchemyAutopilotRepository, AutopilotRun]:
    repo = SqlAlchemyAutopilotRepository(db)
    topic = _topic()
    await repo.add_topic(topic)
    run = AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=topic.candidate_id,
        carousel_project_id=await _carousel(db),
        state=state,
        state_reason=None,
        publish_attempts=publish_attempts,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )
    await repo.add(run)
    return repo, run


def _deps(db: AsyncSession, gateway: _Gateway) -> PublishJobDependencies:
    repo = SqlAlchemyAutopilotRepository(db)
    return PublishJobDependencies(
        runs=repo,
        source=_Source(_snapshot()),
        gateway=gateway,
        notifier=_Notifier(),
        clock=_FixedClock(),
        checkpoint=repo,
        claims=SqlPublishClaims(db),
    )


def _manual_command(project_id: str) -> ManualPublishCommand:
    return ManualPublishCommand(project_id=project_id, caption="cap", image_urls=_SEVEN)


async def _stored(repo: SqlAlchemyAutopilotRepository, run_id: UUID) -> AutopilotRun:
    stored = await repo.get(run_id)
    assert stored is not None
    return stored


# Scenario: Retry after exhaustion calls Graph again
@pytest.mark.asyncio
async def test_retry_after_exhaustion_calls_graph_again(db_session: AsyncSession) -> None:
    repo, run = await _run_in(
        db_session, AutopilotRunState.PUBLISH_FAILED, publish_attempts=3
    )
    retried = await repo.transition(
        TransitionCommand(
            run_id=run.run_id,
            expected=AutopilotRunState.PUBLISH_FAILED,
            new=AutopilotRunState.PUBLISHING,
            reason=REASON_OWNER_RETRY,
        )
    )
    assert retried is True
    assert (await _stored(repo, run.run_id)).publish_attempts == 0

    gateway = _Gateway()
    assert await InstagramPublishJob(_deps(db_session, gateway)).tick() == 1

    assert gateway.opens == 1
    assert gateway.finishes == 1
    published = await _stored(repo, run.run_id)
    assert published.state is AutopilotRunState.PUBLISHED
    assert published.publish_attempts == 0


# Scenario: Start failures do not consume the publish retry budget
@pytest.mark.asyncio
async def test_start_attempts_do_not_consume_the_publish_budget(
    db_session: AsyncSession,
) -> None:
    repo, run = await _run_in(db_session, AutopilotRunState.QUEUED)
    for attempt in (1, 2):
        await repo.note_start_attempt(
            StartAttemptCommand(run_id=run.run_id, attempts=attempt, reason="start")
        )
    queued = await _stored(repo, run.run_id)
    assert queued.start_attempts == 2
    assert queued.publish_attempts == 0
    for expected, new in (
        (AutopilotRunState.QUEUED, AutopilotRunState.GENERATING),
        (AutopilotRunState.GENERATING, AutopilotRunState.AWAITING_OWNER),
        (AutopilotRunState.AWAITING_OWNER, AutopilotRunState.PUBLISHING),
    ):
        await repo.transition(
            TransitionCommand(run_id=run.run_id, expected=expected, new=new, reason="r")
        )
    publishing = await _stored(repo, run.run_id)
    assert publishing.publish_attempts == 0
    due = DueFacts(
        attempts=publishing.publish_attempts,
        updated_at=_NOW,
        now=_NOW,
    )
    assert is_publish_due(due) is True


# Scenario: Manual publish while an autopilot run exists
@pytest.mark.asyncio
async def test_manual_publish_is_refused_while_the_run_awaits_the_owner(
    db_session: AsyncSession,
) -> None:
    _repo, run = await _run_in(db_session, AutopilotRunState.AWAITING_OWNER)
    gateway = _Gateway()
    manual = ManualInstagramPublish(_deps(db_session, gateway))
    assert run.carousel_project_id is not None

    with pytest.raises(ManualPublishRefusedError) as refused:
        await manual.publish(_manual_command(run.carousel_project_id))

    assert refused.value.code == ERR_AUTOPILOT_RUN_ACTIVE
    assert gateway.atomics == 0
    assert gateway.opens == 0


# Scenario: Manual publish of a carousel without a run is idempotent
@pytest.mark.asyncio
async def test_manual_publish_without_a_run_posts_once(db_session: AsyncSession) -> None:
    project_id = await _carousel(db_session)
    gateway = _Gateway()
    manual = ManualInstagramPublish(_deps(db_session, gateway))

    first = await manual.publish(_manual_command(project_id))
    second = await manual.publish(_manual_command(project_id))

    assert gateway.atomics == 1
    assert first.ig_post_id == "atomic-post"
    assert second.ig_post_id == "atomic-post"
    status = await bootstrap_module(
        AutopilotBootstrapDeps(session=db_session)
    ).instagram_status(project_id)
    assert status.state == "published"
    assert status.ig_post_id == "atomic-post"
    assert status.error is None


# Scenario: Manual publish and the worker never publish the same run at once
@pytest.mark.asyncio
async def test_claimed_run_is_skipped_by_manual_route_and_worker(
    db_session: AsyncSession,
) -> None:
    _repo, run = await _run_in(db_session, AutopilotRunState.PUBLISHING)
    claims = SqlPublishClaims(db_session)
    held = await claims.claim_run(
        RunClaim(run_id=run.run_id, now=_NOW, stale_before=_NOW - timedelta(minutes=10))
    )
    assert held is True
    gateway = _Gateway()
    assert run.carousel_project_id is not None

    with pytest.raises(ManualPublishRefusedError) as refused:
        await ManualInstagramPublish(_deps(db_session, gateway)).publish(
            _manual_command(run.carousel_project_id)
        )
    skipped = await InstagramPublishJob(_deps(db_session, gateway)).tick()

    assert refused.value.code == ERR_PUBLISH_IN_PROGRESS
    assert skipped == 0
    assert gateway.opens == 0
    assert gateway.atomics == 0


@pytest.mark.asyncio
async def test_stale_run_claim_is_taken_over(db_session: AsyncSession) -> None:
    _repo, run = await _run_in(db_session, AutopilotRunState.PUBLISHING)
    claims = SqlPublishClaims(db_session)
    old = _NOW - timedelta(hours=1)
    await claims.claim_run(
        RunClaim(run_id=run.run_id, now=old, stale_before=old - timedelta(minutes=10))
    )
    fresh = RunClaim(
        run_id=run.run_id, now=_NOW, stale_before=_NOW - timedelta(minutes=10)
    )
    assert await claims.claim_run(fresh) is True
    assert await claims.claim_run(fresh) is False
    await claims.release_run(run.run_id)
    assert await claims.claim_run(fresh) is True


@pytest.mark.asyncio
async def test_manual_publish_through_a_publishing_run_releases_its_claim(
    db_session: AsyncSession,
) -> None:
    repo, run = await _run_in(db_session, AutopilotRunState.PUBLISHING)
    gateway = _Gateway()
    assert run.carousel_project_id is not None

    outcome = await ManualInstagramPublish(_deps(db_session, gateway)).publish(
        _manual_command(run.carousel_project_id)
    )

    assert outcome.ig_post_id == "post-1"
    assert (await _stored(repo, run.run_id)).state is AutopilotRunState.PUBLISHED
    again = await ManualInstagramPublish(_deps(db_session, gateway)).publish(
        _manual_command(run.carousel_project_id)
    )
    assert again.ig_post_id == "post-1"
    assert gateway.finishes == 1


# Scenario: Undelivered notices are processed oldest first and never skipped
@pytest.mark.asyncio
async def test_event_source_reads_oldest_first_after_the_cursor(
    db_session: AsyncSession,
) -> None:
    run_id = uuid4()
    base = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)
    db_session.add_all([
        _outbox(run_id, base + timedelta(minutes=minute)) for minute in (2, 0, 1)
    ])
    await db_session.flush()
    source = SqlAutopilotEventSource(db_session)

    first = [e for e in await source.recent() if e.run_id == run_id]
    assert [e.created_at.minute for e in first] == [0, 1, 2]
    await source.advance(first[0])
    await source.advance(first[1])
    rest = [e for e in await source.recent() if e.run_id == run_id]

    assert [e.event_id for e in rest] == [first[2].event_id]


# Scenario: Concurrent duplicate topic POSTs
@pytest.mark.asyncio
async def test_a_hash_stored_by_a_concurrent_batch_is_a_duplicate(
    db_session: AsyncSession,
) -> None:
    store = _StaleReadStore(db_session)
    await store.record_served_urls(RecordServedUrls(urls=(_URL_A,), served_at=_NOW))
    service = TopicIntakeService(
        TopicIntakeDependencies(store=store, clock=_Clock(_NOW), daily_cap=3)
    )
    proposal = _proposal("Same signal", _URL_A, 80)
    first = await service.accept(TopicIntakeCommand(proposals=(proposal,)))
    second = await service.accept(TopicIntakeCommand(proposals=(proposal,)))

    assert len(first.queued) == 1
    assert second.queued == ()
    assert second.accepted == ()
    assert [item.reason for item in second.rejected] == [REASON_DUPLICATE_TOPIC]
    count = await db_session.execute(select(func.count()).select_from(TopicCandidateModel))
    assert count.scalar_one() == 1


class _StaleReadStore(SqlAlchemyTopicIntakeStore):
    """Reads as if a concurrent batch had not committed its hash yet."""

    async def ids_for_hashes(self, query: HashLookup) -> dict[str, UUID]:
        del query
        return {}


# Scenario: Over-long URLs are rejected
def test_url_fields_are_capped() -> None:
    long_url = "https://example.com/" + "a" * URL_MAX_CHARS
    with pytest.raises(ValidationError):
        ObservedXPost(
            url=long_url,
            handle="someone",
            text="post",
            observed_at=_NOW,
        )
    with pytest.raises(ValidationError):
        TopicProposal(
            title="t",
            angle="a",
            why_viral="w",
            audience="b",
            niche="n",
            brief="brief",
            sources=[long_url],
            score=50,
        )


def test_lifespan_is_an_async_context_manager() -> None:
    from rag_backend.bootstrap.app_factory import lifespan

    manager = lifespan(FastAPI())
    assert hasattr(manager, "__aenter__")
    assert hasattr(manager, "__aexit__")


def _outbox(run_id: UUID, created_at: datetime) -> EventOutboxModel:
    return EventOutboxModel(
        id=str(uuid4()),
        event_id=str(uuid4()),
        event_type=EVENT_TYPE_READY_FOR_OWNER,
        aggregate_id=str(run_id),
        aggregate_type="autopilot_run",
        version=1,
        payload={"revision": 1},
        metadata_json={},
        event_timestamp=created_at.isoformat(),
        created_at=created_at,
    )
