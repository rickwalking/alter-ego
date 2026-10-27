"""Generation-event retention and dispatch visibility in daily recovery.

Feature: carousel_generation_log_ae0556.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest_asyncio
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.generation_queue.application.dispatcher import (
    Dispatcher,
    DispatcherDependencies,
)
from rag_backend.modules.generation_queue.constants import SCAN_BATCH
from rag_backend.modules.generation_queue.infrastructure.generation_events import (
    SqlGenerationEventRecorder,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    CarouselGenerationEventModel,
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.recovery_store import (
    SqlRecoveryStore,
)
from rag_backend.modules.generation_queue.infrastructure.repository import (
    SqlGenerationRunStore,
)
from tests.integration.queue_flow_db_support import on_postgres, queue_flow_engine
from tests.integration.test_daily_recovery_scan_ae0524 import (
    _DEAD,
    _NOW,
    _PGQ_LOG_DDL,
    _PGQ_LOG_ROW,
    _S,
    _autopilot_run,
    _generation,
    _scan,
    _sessions,
)
from tests.unit.modules.generation_queue.queue_fakes import (
    FakeActiveAutopilot,
    FakeNotices,
    FakeQueue,
)


@pytest_asyncio.fixture(loop_scope="function")
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    async with queue_flow_engine(tmp_path) as built:
        if on_postgres():
            async with built.begin() as conn:
                await conn.execute(_PGQ_LOG_DDL)
        yield built


async def _event_for_run(engine: AsyncEngine, run_id: UUID, age: timedelta) -> UUID:
    project_id = str(uuid4())
    event_id = uuid4()
    async with _sessions(engine)() as session:
        session.add(
            CarouselProjectModel(
                id=project_id,
                topic="Retention",
                title="Retention",
                audience="a",
                niche="n",
                status="completed",
                phase_status="awaiting_human",
                workflow_status="",
            )
        )
        run = await session.get(GenerationRunModel, run_id)
        assert run is not None
        run.carousel_project_id = project_id
        session.add(
            CarouselGenerationEventModel(
                id=event_id,
                generation_run_id=run_id,
                carousel_project_id=project_id,
                kind="autopilot_drive",
                event_type="run_succeeded",
                outcome="succeeded",
                occurred_at=_NOW - age,
                details={},
            )
        )
        await session.commit()
    return event_id


async def test_daily_purge_expires_events_without_blocking_run_purge(
    engine: AsyncEngine,
) -> None:
    """Scenario: Daily purge expires generation events after thirty days"""
    old_run = await _generation(engine, None, "succeeded", (None, timedelta(days=31)))
    recent_run = await _generation(engine, None, "succeeded", (None, timedelta(days=2)))
    dead_run = await _generation(
        engine, None, "dead_letter", ("permanent", timedelta(days=31))
    )
    boundary_run = await _generation(
        engine, None, "succeeded", (None, timedelta(days=30))
    )
    old_event = await _event_for_run(engine, old_run, timedelta(days=31))
    recent_event = await _event_for_run(engine, recent_run, timedelta(days=2))
    dead_event = await _event_for_run(engine, dead_run, timedelta(days=31))
    boundary_event = await _event_for_run(engine, boundary_run, timedelta(days=30))
    if on_postgres():
        async with engine.begin() as conn:
            for job, days in ((91, 40), (92, 3)):
                await conn.execute(
                    _PGQ_LOG_ROW, {"job": job, "created": _NOW - timedelta(days=days)}
                )

    report = await _scan(engine).run_once()

    assert report.purged_runs == 1
    assert report.purged_logs == (1 if on_postgres() else 0)
    async with _sessions(engine)() as session:
        events = set(await session.scalars(select(CarouselGenerationEventModel.id)))
        runs = set(await session.scalars(select(GenerationRunModel.id)))
    assert events == {recent_event, boundary_event}
    assert old_event not in events
    assert dead_event not in events
    assert runs == {recent_run, dead_run, boundary_run}


async def test_daily_purge_deletes_expired_events_in_bounded_batches(
    engine: AsyncEngine,
) -> None:
    """Scenario: Daily purge expires generation events after thirty days"""
    dead_run = await _generation(
        engine, None, "dead_letter", ("permanent", timedelta(days=31))
    )
    expired = {
        await _event_for_run(engine, dead_run, timedelta(days=31))
        for _ in range(SCAN_BATCH * 2 + 1)
    }
    recent = await _event_for_run(engine, dead_run, timedelta(days=2))
    deletes: list[str] = []

    def capture_delete(*args: object) -> None:
        statement = str(args[2])
        if "delete from carousel_generation_events" in statement.lower():
            deletes.append(statement)

    sqlalchemy_event.listen(engine.sync_engine, "before_cursor_execute", capture_delete)
    try:
        report = await SqlRecoveryStore(_sessions(engine)).purge(
            _NOW - timedelta(days=30)
        )
    finally:
        sqlalchemy_event.remove(
            engine.sync_engine, "before_cursor_execute", capture_delete
        )

    assert report == (0, 0)
    assert len(deletes) == 3
    async with _sessions(engine)() as session:
        remaining = set(await session.scalars(select(CarouselGenerationEventModel.id)))
    assert remaining == {recent}
    assert expired.isdisjoint(remaining)


async def test_daily_revive_becomes_a_visible_queued_event(
    engine: AsyncEngine,
) -> None:
    """Scenario: A failed and retried run exposes safe failure and retry history"""
    autopilot_id = await _autopilot_run(engine, _S.ESCALATED, _DEAD, timedelta(hours=6))
    run_id = await _generation(
        engine, autopilot_id, "dead_letter", ("transient", timedelta(hours=6))
    )
    project_id = str(uuid4())
    async with _sessions(engine)() as session:
        session.add(
            CarouselProjectModel(
                id=project_id,
                topic="Recovery event",
                title="Recovery event",
                audience="a",
                niche="n",
                status="generating",
                phase_status="in_progress",
                workflow_status="",
            )
        )
        parent = await session.get(AutopilotRunModel, UUID(autopilot_id))
        assert parent is not None
        parent.carousel_project_id = project_id
        await session.commit()

    await _scan(engine).run_once()
    dispatcher = Dispatcher(
        DispatcherDependencies(
            store=SqlGenerationRunStore(_sessions(engine)),
            queue=FakeQueue(),
            autopilot=FakeActiveAutopilot(),
            notices=FakeNotices(),
            events=SqlGenerationEventRecorder(_sessions(engine)),
        )
    )
    report = await dispatcher.run_once()
    assert report.dispatched == 1
    async with _sessions(engine)() as session:
        event_types = await session.scalars(
            select(CarouselGenerationEventModel.event_type).where(
                CarouselGenerationEventModel.generation_run_id == run_id
            )
        )

    assert list(event_types) == ["run_queued"]
