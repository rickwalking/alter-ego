"""Backlog intake, "Gerar agora" and dead-letter retries on a real database (SQLite).

Feature: backend/tests/features/telegram_queue_flow_ae0523.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from rag_backend.modules.autopilot.application.backlog_promotion import (
    PromotionDependencies,
    promote_waiting,
)
from rag_backend.modules.autopilot.application.topic_intake import (
    TopicIntakeCommand,
    TopicIntakeDependencies,
    TopicIntakeResult,
    TopicIntakeService,
)
from rag_backend.modules.autopilot.domain.backlog import (
    BacklogChange,
    BacklogWindow,
    GenerateNowCommand,
)
from rag_backend.modules.autopilot.domain.dead_letter import RetryFailedCommand
from rag_backend.modules.autopilot.domain.intake import ProposalInput
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.ports import DayWindow
from rag_backend.modules.autopilot.domain.topic_text import sao_paulo_day
from rag_backend.modules.autopilot.infrastructure.backlog_store import SqlBacklogStore
from rag_backend.modules.autopilot.infrastructure.dead_letter_runs import (
    SqlDeadLetterRuns,
)
from rag_backend.modules.autopilot.infrastructure.intake_store import (
    SqlAlchemyTopicIntakeStore,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.queue_constants import (
    CANDIDATE_BACKLOG,
    CANDIDATE_BACKLOG_EXPIRED,
    CANDIDATE_BACKLOG_NOTED,
    CANDIDATE_GENERATE_NOW,
    CANDIDATE_PROMOTED,
    REASON_BACKLOG_FULL,
    REASON_DEAD_DISCARD,
    REASON_DEAD_RETRY,
)
from tests.integration.autopilot_topic_support import _Clock, _serve
from tests.integration.queue_flow_db_support import queue_flow_engine

_NOW = datetime(2026, 10, 24, 14, 0, tzinfo=UTC)
_WORDS = (
    "robots fold laundry",
    "quantum chips arrive",
    "solar farms float",
    "satellites map forests",
    "batteries recycle lithium",
    "drones deliver insulin",
)
_DEAD = "queue_dead_letter:permanent"
_S = AutopilotRunState


@pytest_asyncio.fixture(loop_scope="function")
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    async with queue_flow_engine(tmp_path) as built:
        yield built


def _sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def _url(index: int) -> str:
    return f"https://news.ycombinator.com/item?id={1000 + index}"


def _proposal(index: int, score: int) -> ProposalInput:
    title = _WORDS[index]
    return ProposalInput(
        title=title,
        angle="operator view",
        why_viral="three launches in one week",
        audience="builders",
        niche="ai",
        brief=f"A plain brief about {title}.",
        sources=(_url(index),),
        score=score,
        content_mode="pov",
        thesis_draft="Quem decide o que construir ainda é o dev.",
        index=index,
    )


async def _accept(
    engine: AsyncEngine, proposals: tuple[ProposalInput, ...], cap: int
) -> TopicIntakeResult:
    await _serve(engine, tuple(p.sources[0] for p in proposals), _NOW)
    async with _sessions(engine)() as session:
        store = SqlAlchemyTopicIntakeStore(session)
        service = TopicIntakeService(
            TopicIntakeDependencies(
                store=store,
                clock=_Clock(_NOW),
                daily_cap=cap,
                posts=store,
                backlog=SqlBacklogStore(session),
            )
        )
        return await service.accept(TopicIntakeCommand(proposals=proposals))


async def _seed_topic(
    engine: AsyncEngine, status: str, created_at: datetime, title: str = ""
) -> UUID:
    topic_id = uuid4()
    async with _sessions(engine)() as session:
        session.add(
            TopicCandidateModel(
                id=topic_id,
                title=title or f"seeded {topic_id.hex[:6]}",
                angle="a",
                why_viral="w",
                audience="builders",
                niche="ai",
                brief="b",
                sources=["https://example.com/a"],
                score=50,
                signal_hash=uuid4().hex,
                status=status,
                created_at=created_at,
            )
        )
        await session.flush()
        await session.commit()
    return topic_id


async def _seed_run(
    engine: AsyncEngine, topic_id: UUID, state: _S, reason: str | None = None
) -> UUID:
    run_id = uuid4()
    async with _sessions(engine)() as session:
        session.add(
            AutopilotRunModel(
                id=run_id,
                topic_candidate_id=topic_id,
                state=state.value,
                state_reason=reason,
                publish_attempts=0,
                telegram_message_ids=[],
                created_at=_NOW - timedelta(minutes=5),
                updated_at=_NOW - timedelta(minutes=5),
            )
        )
        await session.commit()
    return run_id


async def _statuses(engine: AsyncEngine) -> dict[str, str]:
    async with _sessions(engine)() as session:
        rows = await session.execute(
            select(TopicCandidateModel.title, TopicCandidateModel.status)
        )
    return {str(title): str(status) for title, status in rows.all()}


async def _topic_id(session: AsyncSession, title: str) -> UUID:
    found = await session.scalar(
        select(TopicCandidateModel.id).where(TopicCandidateModel.title == title)
    )
    assert found is not None
    return found


async def _runs_for(engine: AsyncEngine, topic_id: UUID) -> int:
    async with _sessions(engine)() as session:
        counted = await session.scalar(
            select(func.count())
            .select_from(AutopilotRunModel)
            .where(AutopilotRunModel.topic_candidate_id == topic_id)
        )
    return int(counted or 0)


async def test_themes_over_the_daily_cap_wait_in_the_backlog(
    engine: AsyncEngine,
) -> None:
    """Scenario: Themes over the daily cap wait in the backlog"""
    result = await _accept(
        engine, (_proposal(0, 90), _proposal(1, 70), _proposal(2, 50)), cap=1
    )
    assert len(result.queued) == 1
    statuses = await _statuses(engine)
    assert statuses[_WORDS[0]] == "accepted"
    assert statuses[_WORDS[1]] == CANDIDATE_BACKLOG
    assert statuses[_WORDS[2]] == CANDIDATE_BACKLOG


async def test_the_backlog_never_holds_more_than_ten_themes(
    engine: AsyncEngine,
) -> None:
    """Scenario: The backlog never holds more than 10 themes"""
    for _ in range(9):
        await _seed_topic(engine, CANDIDATE_BACKLOG_NOTED, _NOW - timedelta(hours=1))
    day_topic = await _seed_topic(engine, "promoted", _NOW - timedelta(hours=2))
    await _seed_run(engine, day_topic, _S.QUEUED)
    result = await _accept(
        engine, (_proposal(0, 90), _proposal(1, 70), _proposal(2, 50)), cap=1
    )
    assert result.queued == ()
    statuses = await _statuses(engine)
    assert statuses[_WORDS[0]] == CANDIDATE_BACKLOG
    assert statuses[_WORDS[1]] == "accepted"
    assert statuses[_WORDS[2]] == "accepted"
    full = [r for r in result.rejected if r.reason == REASON_BACKLOG_FULL]
    assert sorted(r.title for r in full) == sorted((_WORDS[1], _WORDS[2]))
    assert all(
        r.title not in (_WORDS[1], _WORDS[2])
        for r in result.rejected
        if r.reason != REASON_BACKLOG_FULL
    )


async def test_the_next_mornings_slots_go_to_the_backlog_first(
    engine: AsyncEngine,
) -> None:
    """Scenario: The next morning's slots go to the backlog first"""
    oldest = await _seed_topic(
        engine, CANDIDATE_BACKLOG_NOTED, _NOW - timedelta(days=3), "oldest"
    )
    older = await _seed_topic(
        engine, CANDIDATE_BACKLOG_NOTED, _NOW - timedelta(days=2), "older"
    )
    newest = await _seed_topic(
        engine, CANDIDATE_BACKLOG_NOTED, _NOW - timedelta(days=1), "newest"
    )
    result = await _accept(engine, (_proposal(0, 90), _proposal(1, 70)), cap=2)
    assert len(result.queued) == 2
    statuses = await _statuses(engine)
    assert statuses["oldest"] == CANDIDATE_PROMOTED
    assert statuses["older"] == CANDIDATE_PROMOTED
    assert statuses["newest"] == CANDIDATE_BACKLOG_NOTED
    assert statuses[_WORDS[0]] == CANDIDATE_BACKLOG
    assert statuses[_WORDS[1]] == CANDIDATE_BACKLOG
    assert await _runs_for(engine, oldest) == 1
    assert await _runs_for(engine, older) == 1
    assert await _runs_for(engine, newest) == 0


async def test_a_theme_added_to_the_backlog_today_waits(engine: AsyncEngine) -> None:
    """Scenario: A theme added to the backlog today waits until tomorrow"""
    day_start, _ = sao_paulo_day(_NOW)
    today = await _seed_topic(
        engine, CANDIDATE_BACKLOG, day_start + timedelta(minutes=1), "today"
    )
    result = await _accept(engine, (_proposal(0, 90),), cap=2)
    assert len(result.queued) == 1
    assert (await _statuses(engine))["today"] == CANDIDATE_BACKLOG
    assert await _runs_for(engine, today) == 0


async def test_generate_now_is_outside_the_daily_cap_and_happens_once(
    engine: AsyncEngine,
) -> None:
    """Scenario: "Gerar agora" queues a backlog theme at once, outside the daily cap"""
    used = await _seed_topic(engine, "accepted", _NOW - timedelta(hours=1))
    await _seed_run(engine, used, _S.GENERATING)
    theme = await _seed_topic(
        engine, CANDIDATE_BACKLOG_NOTED, _NOW - timedelta(days=1), "wait"
    )
    day_start, day_end = sao_paulo_day(_NOW)
    async with _sessions(engine)() as session:
        store = SqlBacklogStore(session)
        command = GenerateNowCommand(
            candidate_id=theme, run_id=uuid4(), created_at=_NOW
        )
        generated = await store.generate_now(command)
        again = await store.generate_now(
            GenerateNowCommand(candidate_id=theme, run_id=uuid4(), created_at=_NOW)
        )
        counted = await SqlAlchemyTopicIntakeStore(session).runs_created_between(
            DayWindow(start=day_start, end=day_end)
        )
        await session.commit()
    assert generated is not None
    assert generated.title == "wait"
    assert again is None
    assert counted == 1
    assert (await _statuses(engine))["wait"] == CANDIDATE_GENERATE_NOW
    assert await _runs_for(engine, theme) == 1


async def test_backlog_store_lists_and_moves_only_waiting_themes(
    engine: AsyncEngine,
) -> None:
    """Scenario: A backlog theme expires after 7 days with one note"""
    await _seed_topic(engine, CANDIDATE_BACKLOG, _NOW - timedelta(hours=1), "new")
    await _seed_topic(engine, CANDIDATE_BACKLOG_NOTED, _NOW - timedelta(days=8), "old")
    await _seed_topic(engine, CANDIDATE_PROMOTED, _NOW - timedelta(days=9), "gone")
    async with _sessions(engine)() as session:
        store = SqlBacklogStore(session)
        unannounced = [t.title for t in await store.unannounced()]
        window = BacklogWindow(since=_NOW - timedelta(days=30), before=_NOW)
        waiting = [t.title for t in await store.waiting(window)]
        old = [t for t in await store.waiting(window) if t.title == "old"]
        gone = await _topic_id(session, "gone")
        moved = await store.change(
            BacklogChange(
                candidate_ids=(old[0].candidate_id, gone),
                status=CANDIDATE_BACKLOG_EXPIRED,
            )
        )
        await session.commit()
    assert unannounced == ["new"]
    assert waiting == ["old", "new"]
    assert moved == (old[0].candidate_id,)
    assert (await _statuses(engine))["gone"] == CANDIDATE_PROMOTED
    assert (await _statuses(engine))["old"] == CANDIDATE_BACKLOG_EXPIRED


async def test_retry_and_discard_of_failed_dead_letters(engine: AsyncEngine) -> None:
    """Scenario: Retry restarts a run that died before it started"""
    topic = await _seed_topic(engine, "promoted", _NOW - timedelta(hours=1))
    failed = await _seed_run(engine, topic, _S.FAILED, _DEAD)
    other = await _seed_run(
        engine, await _seed_topic(engine, "x", _NOW), _S.FAILED, _DEAD
    )
    engine_error = await _seed_run(
        engine, await _seed_topic(engine, "y", _NOW), _S.FAILED, "engine_error:X"
    )
    new_run = uuid4()
    async with _sessions(engine)() as session:
        dead = SqlDeadLetterRuns(session)
        retried = await dead.retry_failed(
            RetryFailedCommand(run_id=failed, new_run_id=new_run, created_at=_NOW)
        )
        twice = await dead.retry_failed(
            RetryFailedCommand(run_id=failed, new_run_id=uuid4(), created_at=_NOW)
        )
        discarded = await dead.discard_failed(other)
        refused = await dead.discard_failed(engine_error)
        await session.commit()
        reasons = dict(
            (
                await session.execute(
                    select(AutopilotRunModel.id, AutopilotRunModel.state_reason)
                )
            ).all()
        )
        queued = await session.get(AutopilotRunModel, new_run)
    assert (retried, twice, discarded, refused) == (True, False, True, False)
    assert reasons[failed] == REASON_DEAD_RETRY
    assert reasons[other] == REASON_DEAD_DISCARD
    assert reasons[engine_error] == "engine_error:X"
    assert queued is not None
    assert queued.state == _S.QUEUED.value
    assert queued.topic_candidate_id == topic


async def _promote(engine: AsyncEngine, cap: int) -> int:
    async with _sessions(engine)() as session:
        return await promote_waiting(
            PromotionDependencies(
                store=SqlAlchemyTopicIntakeStore(session),
                backlog=SqlBacklogStore(session),
                clock=_Clock(_NOW),
                daily_cap=cap,
            )
        )


async def test_waiting_themes_start_without_a_scout_batch(engine: AsyncEngine) -> None:
    """Scenario: Waiting themes start in the morning even without a scout batch"""
    older = await _seed_topic(
        engine, CANDIDATE_BACKLOG_NOTED, _NOW - timedelta(days=2), "older"
    )
    newer = await _seed_topic(
        engine, CANDIDATE_BACKLOG_NOTED, _NOW - timedelta(days=1), "newer"
    )
    assert await _promote(engine, cap=3) == 2
    assert await _runs_for(engine, older) == 1
    assert await _runs_for(engine, newer) == 1
    statuses = await _statuses(engine)
    assert statuses["older"] == statuses["newer"] == CANDIDATE_PROMOTED


async def test_the_morning_promotion_fills_only_free_slots_once(
    engine: AsyncEngine,
) -> None:
    """Scenario: The morning promotion fills only the free slots, once"""
    for _ in range(2):
        used = await _seed_topic(engine, "promoted", _NOW - timedelta(hours=2))
        await _seed_run(engine, used, _S.QUEUED)
    oldest = await _seed_topic(
        engine, CANDIDATE_BACKLOG_NOTED, _NOW - timedelta(days=3), "oldest"
    )
    later = await _seed_topic(
        engine, CANDIDATE_BACKLOG_NOTED, _NOW - timedelta(days=1), "later"
    )
    assert await _promote(engine, cap=3) == 1
    assert await _promote(engine, cap=3) == 0
    assert await _runs_for(engine, oldest) == 1
    assert await _runs_for(engine, later) == 0
    assert (await _statuses(engine))["later"] == CANDIDATE_BACKLOG_NOTED
