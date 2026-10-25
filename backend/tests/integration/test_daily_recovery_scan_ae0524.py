"""The daily recovery scan's store and revivals (Postgres in CI, else SQLite).

Feature: backend/tests/features/daily_recovery_scan_ae0524.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.bootstrap import AutopilotTickConfig
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.queue_bridge import AutopilotQueueBridge
from rag_backend.modules.autopilot.queue_constants import REASON_DAILY_RECOVERY
from rag_backend.modules.generation_queue.application.recovery_scan import (
    DailyRecoveryScan,
    DailyScanDependencies,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.recovery_store import (
    SqlRecoveryStore,
)
from tests.integration.queue_flow_db_support import on_postgres, queue_flow_engine

_NOW = datetime.now(UTC).replace(microsecond=0)
_S = AutopilotRunState
_DEAD = "queue_dead_letter:run_budget_exhausted"
_PGQ_LOG_DDL = text("CREATE TABLE pgqueuer_log (job_id BIGINT, created TIMESTAMPTZ)")
_PGQ_LOG_ROW = text(
    "INSERT INTO pgqueuer_log (job_id, created) VALUES (:job, :created)"
)


class _Clock:
    def now(self) -> datetime:
        return _NOW


@pytest_asyncio.fixture(loop_scope="function")
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    async with queue_flow_engine(tmp_path) as built:
        if on_postgres():
            async with built.begin() as conn:
                await conn.execute(_PGQ_LOG_DDL)
        yield built


def _sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def _bridge(engine: AsyncEngine) -> AutopilotQueueBridge:
    config = AutopilotTickConfig(
        owner_user_id="owner", engine_factory=lambda: None, stale_after_seconds=180
    )
    return AutopilotQueueBridge(
        config=config, sessions=_sessions(engine), retryable=lambda exc: False
    )


async def _autopilot_run(
    engine: AsyncEngine, state: _S, reason: str | None, age: timedelta
) -> str:
    topic_id, run_id = uuid4(), uuid4()
    moment = _NOW - age
    async with _sessions(engine)() as session:
        session.add(
            TopicCandidateModel(
                id=topic_id,
                title=f"t {run_id.hex[:6]}",
                angle="a",
                why_viral="w",
                audience="a",
                niche="n",
                brief="b",
                sources=["https://example.com/a"],
                score=1,
                signal_hash=uuid4().hex,
                status="promoted",
            )
        )
        await session.flush()
        session.add(
            AutopilotRunModel(
                id=run_id,
                topic_candidate_id=topic_id,
                state=state.value,
                state_reason=reason,
                publish_attempts=0,
                telegram_message_ids=[],
                created_at=moment,
                updated_at=moment,
            )
        )
        await session.commit()
    return str(run_id)


async def _generation(
    engine: AsyncEngine,
    autopilot_run_id: str | None,
    status: str,
    detail: tuple[str | None, timedelta],
) -> UUID:
    code, age = detail
    run_id = uuid4()
    moment = _NOW - age
    async with _sessions(engine)() as session:
        session.add(
            GenerationRunModel(
                id=run_id,
                kind="autopilot_drive",
                dedupe_key=f"autopilot:{autopilot_run_id or run_id}",
                status=status,
                payload={"autopilot_run_id": autopilot_run_id or ""},
                autopilot_run_id=autopilot_run_id,
                attempts=2,
                phase_attempts={"content": 2},
                last_phase="content",
                last_error_code=code,
                created_at=moment,
                started_at=moment,
                finished_at=moment,
                updated_at=moment,
            )
        )
        await session.commit()
    return run_id


async def _run_state(engine: AsyncEngine, run_id: str) -> tuple[str, str | None]:
    async with _sessions(engine)() as session:
        row = await session.get(AutopilotRunModel, UUID(run_id))
    assert row is not None
    return row.state, row.state_reason


async def _generation_row(engine: AsyncEngine, run_id: UUID) -> GenerationRunModel:
    async with _sessions(engine)() as session:
        row = await session.get(GenerationRunModel, run_id)
    assert row is not None
    return row


def _scan(engine: AsyncEngine) -> DailyRecoveryScan:
    return DailyRecoveryScan(
        DailyScanDependencies(
            store=SqlRecoveryStore(_sessions(engine)),
            autopilot=_bridge(engine),
            clock=_Clock(),
        )
    )


async def test_a_recent_transient_dead_letter_is_retried_once(
    engine: AsyncEngine,
) -> None:
    """Scenario: A recent transient dead letter is retried once"""
    run = await _autopilot_run(engine, _S.ESCALATED, _DEAD, timedelta(hours=20))
    dead = await _generation(
        engine, run, "dead_letter", ("run_budget_exhausted", timedelta(hours=20))
    )
    first = await _scan(engine).run_once()
    second = await _scan(engine).run_once()
    assert (first.recovered, second.recovered) == (1, 0)
    assert await _run_state(engine, run) == (_S.GENERATING.value, REASON_DAILY_RECOVERY)
    row = await _generation_row(engine, dead)
    assert row.status == "queued"
    assert row.payload["recovery_attempt"] is True
    assert row.phase_attempts == {}


async def test_a_dead_letter_pedro_resolved_is_not_retried(engine: AsyncEngine) -> None:
    """Scenario: A dead letter Pedro already resolved is not retried"""
    run = await _autopilot_run(
        engine, _S.REJECTED, "owner_queue_discard", timedelta(hours=5)
    )
    dead = await _generation(
        engine, run, "dead_letter", ("transient", timedelta(hours=5))
    )
    report = await _scan(engine).run_once()
    assert report.recovered == 0
    assert await _run_state(engine, run) == (_S.REJECTED.value, "owner_queue_discard")
    row = await _generation_row(engine, dead)
    assert row.status == "dead_letter"
    assert row.payload["recovery_attempt"] is True


async def test_permanent_and_old_dead_letters_are_left_alone(
    engine: AsyncEngine,
) -> None:
    """Scenario: A permanent or old dead letter is left alone"""
    permanent = await _autopilot_run(engine, _S.ESCALATED, _DEAD, timedelta(hours=5))
    await _generation(
        engine, permanent, "dead_letter", ("permanent", timedelta(hours=5))
    )
    old = await _autopilot_run(engine, _S.ESCALATED, _DEAD, timedelta(days=8))
    await _generation(engine, old, "dead_letter", ("transient", timedelta(days=8)))
    report = await _scan(engine).run_once()
    assert report.recovered == 0
    assert report.still_dead == 1
    assert (await _run_state(engine, permanent))[0] == _S.ESCALATED.value
    assert (await _run_state(engine, old))[0] == _S.ESCALATED.value


async def test_a_stale_escalation_resumes(engine: AsyncEngine) -> None:
    """Scenario: A stale autopilot escalation resumes from its checkpoint"""
    stale = await _autopilot_run(engine, _S.ESCALATED, "run_stale", timedelta(hours=10))
    too_old = await _autopilot_run(
        engine, _S.ESCALATED, "run_stale", timedelta(hours=80)
    )
    other = await _autopilot_run(
        engine, _S.ESCALATED, "engine_error:X", timedelta(hours=10)
    )
    report = await _scan(engine).run_once()
    assert report.recovered == 1
    assert await _run_state(engine, stale) == (
        _S.GENERATING.value,
        REASON_DAILY_RECOVERY,
    )
    assert (await _run_state(engine, too_old))[0] == _S.ESCALATED.value
    assert (await _run_state(engine, other))[0] == _S.ESCALATED.value


async def test_parked_dashboard_projects_are_listed(engine: AsyncEngine) -> None:
    """Scenario: Parked dashboard projects are listed, not resumed"""
    async with _sessions(engine)() as session:
        session.add(
            CarouselProjectModel(
                id=str(uuid4()),
                topic="Carrossel do painel",
                title="Carrossel do painel",
                audience="a",
                niche="n",
                status="drafting",
                phase_status="in_progress",
                workflow_status="",
            )
        )
        await session.commit()
    report = await _scan(engine).run_once()
    assert (
        report.interactive == ("Carrossel do painel",) or len(report.interactive) == 1
    )
    async with _sessions(engine)() as session:
        queued = (await session.execute(select(GenerationRunModel.id))).all()
    assert queued == []


async def test_old_succeeded_runs_are_purged(engine: AsyncEngine) -> None:
    """Scenario: Old succeeded runs and PgQueuer logs are purged"""
    old = await _generation(engine, None, "succeeded", (None, timedelta(days=31)))
    recent = await _generation(engine, None, "succeeded", (None, timedelta(days=2)))
    if on_postgres():
        async with engine.begin() as conn:
            for job, days in ((1, 40), (2, 3)):
                await conn.execute(
                    _PGQ_LOG_ROW, {"job": job, "created": _NOW - timedelta(days=days)}
                )
    report = await _scan(engine).run_once()
    assert (report.purged_runs, report.purged_logs) == (1, 1 if on_postgres() else 0)
    async with _sessions(engine)() as session:
        left = {
            row[0]
            for row in (await session.execute(select(GenerationRunModel.id))).all()
        }
    assert left == {recent}
    assert old not in left


async def _queued_runs_for_topic(
    engine: AsyncEngine, run_id: str
) -> list[AutopilotRunModel]:
    async with _sessions(engine)() as session:
        old = await session.get(AutopilotRunModel, UUID(run_id))
        assert old is not None
        rows = await session.execute(
            select(AutopilotRunModel).where(
                AutopilotRunModel.topic_candidate_id == old.topic_candidate_id,
                AutopilotRunModel.id != old.id,
            )
        )
        return list(rows.scalars().all())


async def test_a_failed_run_is_retried_once_per_theme(engine: AsyncEngine) -> None:
    """Scenario: A theme the scan already retried is not retried again"""
    failed = await _autopilot_run(engine, _S.FAILED, _DEAD, timedelta(hours=6))
    await _generation(engine, failed, "dead_letter", ("transient", timedelta(hours=6)))
    first = await _scan(engine).run_once()
    retries = await _queued_runs_for_topic(engine, failed)
    assert first.recovered == 1
    assert len(retries) == 1
    retry = retries[0]
    assert "daily_recovery" in str(retry.telegram_message_ids)
    async with _sessions(engine)() as session:
        stored = await session.get(AutopilotRunModel, retry.id)
        assert stored is not None
        stored.state = _S.FAILED.value
        stored.state_reason = _DEAD
        await session.commit()
    await _generation(
        engine, str(retry.id), "dead_letter", ("transient", timedelta(hours=1))
    )
    second = await _scan(engine).run_once()
    assert second.recovered == 0
    assert len(await _queued_runs_for_topic(engine, failed)) == 1


async def test_a_stale_run_is_resumed_once_and_not_too_early(
    engine: AsyncEngine,
) -> None:
    """Scenario: A stale run is resumed only once, and not in its first hour"""
    stale = await _autopilot_run(engine, _S.ESCALATED, "run_stale", timedelta(hours=5))
    fresh = await _autopilot_run(
        engine, _S.ESCALATED, "run_stale", timedelta(minutes=20)
    )
    first = await _scan(engine).run_once()
    assert first.recovered == 1
    assert (await _run_state(engine, fresh))[0] == _S.ESCALATED.value
    async with _sessions(engine)() as session:
        again = await session.get(AutopilotRunModel, UUID(stale))
        assert again is not None
        again.state = _S.ESCALATED.value
        again.state_reason = "run_stale"
        again.updated_at = _NOW - timedelta(hours=2)
        await session.commit()
    second = await _scan(engine).run_once()
    assert second.recovered == 0
    assert (await _run_state(engine, stale)) == (_S.ESCALATED.value, "run_stale")


async def test_tried_dead_letters_do_not_hide_newer_ones(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: A recent transient dead letter is retried once"""
    from rag_backend.modules.generation_queue.infrastructure import recovery_store

    monkeypatch.setattr(recovery_store, "SCAN_BATCH", 1)
    store = SqlRecoveryStore(_sessions(engine))
    tried = await _generation(
        engine, str(uuid4()), "dead_letter", ("transient", timedelta(hours=9))
    )
    assert await store.mark_attempted(tried)
    assert not await store.mark_attempted(tried)
    newer = await _generation(
        engine, str(uuid4()), "dead_letter", ("transient", timedelta(hours=2))
    )
    found = await store.recoverable(_NOW - timedelta(days=7))
    assert [d.generation_run_id for d in found] == [newer]
