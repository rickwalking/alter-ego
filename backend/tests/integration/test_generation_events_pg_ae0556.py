"""Generation-event keyset reads with production foreign keys.

Feature: carousel_generation_log_ae0556.feature
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.generation_queue.application.generation_events import (
    generation_event_scope,
    record_generation_event,
)
from rag_backend.modules.generation_queue.domain.generation_events import (
    GenerationEventInput,
    GenerationEventRun,
    GenerationLogPage,
    GenerationLogQuery,
)
from rag_backend.modules.generation_queue.domain.models import GenerationKind
from rag_backend.modules.generation_queue.infrastructure.generation_events import (
    SqlGenerationEventRecorder,
    read_generation_log,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    CarouselGenerationEventModel,
    GenerationRunModel,
)
from tests.integration.queue_flow_db_support import on_postgres, queue_flow_engine

BASE = datetime(2026, 10, 26, 12, tzinfo=UTC)


def _sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def test_keyset_store_pages_remain_stable_on_postgres(tmp_path: Path) -> None:
    """Scenario: Generation log pages are stable during new events"""
    async with queue_flow_engine(tmp_path) as engine:
        sessions = _sessions(engine)
        project_id = str(uuid4())
        run_id = uuid4()
        async with sessions() as session:
            session.add(
                CarouselProjectModel(
                    id=project_id,
                    topic="Postgres events",
                    title="Postgres events",
                    audience="QA",
                    niche="QA",
                    status="completed",
                    phase_status="awaiting_human",
                    workflow_status="",
                )
            )
            session.add(
                GenerationRunModel(
                    id=run_id,
                    kind="workflow_resume",
                    dedupe_key=f"resume:{project_id}:1",
                    status="running",
                    payload={},
                    carousel_project_id=project_id,
                    attempts=1,
                    phase_attempts={},
                    created_at=BASE,
                    updated_at=BASE,
                )
            )
            await session.commit()
        run = GenerationEventRun(
            id=run_id,
            kind=GenerationKind.WORKFLOW_RESUME,
            carousel_project_id=project_id,
        )
        original: list[str] = []
        async with generation_event_scope(run, SqlGenerationEventRecorder(sessions)):
            for index in range(3):
                event = GenerationEventInput(
                    event_type="phase_succeeded",
                    outcome="succeeded",
                    occurred_at=BASE,
                )
                original.append(str(event.id))
                assert await record_generation_event(event)
            first = await _page(
                sessions, GenerationLogQuery(project_id=project_id, limit=2)
            )
            newer = GenerationEventInput(
                event_type="run_started",
                outcome="running",
                occurred_at=BASE + timedelta(seconds=1),
            )
            assert await record_generation_event(newer)
            second = await _page(
                sessions,
                GenerationLogQuery(
                    project_id=project_id, limit=2, before=first.next_cursor
                ),
            )
        if on_postgres():
            async with sessions() as session:
                await session.execute(
                    delete(GenerationRunModel).where(GenerationRunModel.id == run_id)
                )
                remaining = await session.scalar(
                    select(func.count()).select_from(CarouselGenerationEventModel)
                )
            assert remaining == 0

    assert len(first.events) == 2
    assert first.next_cursor is not None
    assert len(second.events) == 1
    assert second.next_cursor is None
    returned = [str(event.id) for event in (*first.events, *second.events)]
    assert len(returned) == len(set(returned)) == 3
    assert set(returned) == set(original)
    assert str(newer.id) not in returned


async def test_carousel_parent_cascade_removes_events(tmp_path: Path) -> None:
    """Scenario: Daily purge expires generation events after thirty days"""
    async with queue_flow_engine(tmp_path) as engine:
        sessions = _sessions(engine)
        project_id = str(uuid4())
        run_id = uuid4()
        async with sessions() as session:
            session.add(
                CarouselProjectModel(
                    id=project_id,
                    topic="Cascade",
                    title="Cascade",
                    audience="QA",
                    niche="QA",
                    status="completed",
                    phase_status="awaiting_human",
                    workflow_status="",
                )
            )
            session.add(
                GenerationRunModel(
                    id=run_id,
                    kind="workflow_resume",
                    dedupe_key=f"resume:{project_id}:cascade",
                    status="running",
                    payload={},
                    carousel_project_id=project_id,
                    attempts=1,
                    phase_attempts={},
                    created_at=BASE,
                    updated_at=BASE,
                )
            )
            await session.commit()
        run = GenerationEventRun(
            id=run_id,
            kind=GenerationKind.WORKFLOW_RESUME,
            carousel_project_id=project_id,
        )
        async with generation_event_scope(run, SqlGenerationEventRecorder(sessions)):
            assert await record_generation_event(
                GenerationEventInput(event_type="run_started", outcome="running")
            )
        async with sessions() as session:
            if not on_postgres():
                await session.execute(text("PRAGMA foreign_keys = ON"))
            await session.execute(
                delete(CarouselProjectModel).where(
                    CarouselProjectModel.id == project_id
                )
            )
            remaining = await session.scalar(
                select(func.count()).select_from(CarouselGenerationEventModel)
            )

    assert remaining == 0


async def _page(
    sessions: async_sessionmaker[AsyncSession], query: GenerationLogQuery
) -> GenerationLogPage:
    async with sessions() as session:
        return await read_generation_log(session, query)
