"""Barrier-controlled daily recovery and owner-retry races.

Feature: backend/tests/features/daily_recovery_scan_ae0553.feature
"""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)
from rag_backend.modules.autopilot import queue_bridge
from rag_backend.modules.autopilot.constants import EVENT_TYPE_STATE_CHANGED
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.generation_queue.constants import (
    ACTIVE_STATUSES,
    AUDIT_CAROUSEL_REPROCESS,
)
from rag_backend.modules.generation_queue.domain.recovery import ParkedDrive
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from tests.integration.queue_flow_db_support import on_postgres
from tests.integration.test_daily_recovery_scan_ae0524 import (
    _autopilot_run,
    _bridge,
    _generation,
    _sessions,
    engine,
)
from tests.integration.test_queue_retry_ae0523 import _tap_retry

__all__ = ["engine"]

_S = AutopilotRunState
_DEAD = "queue_dead_letter:run_budget_exhausted"


@dataclass(frozen=True, kw_only=True)
class _RaceCase:
    run_id: str
    dead_id: UUID
    state: _S
    drive: ParkedDrive


async def _setup_case(engine: AsyncEngine, state: _S) -> _RaceCase:
    run_id = await _autopilot_run(engine, state, _DEAD, timedelta(hours=5))
    dead_id = await _generation(
        engine, run_id, "dead_letter", ("transient", timedelta(hours=5))
    )
    return _RaceCase(
        run_id=run_id,
        dead_id=dead_id,
        state=state,
        drive=ParkedDrive(generation_run_id=dead_id, autopilot_run_id=run_id),
    )


async def _scan_race(
    engine: AsyncEngine, case: _RaceCase, monkeypatch: pytest.MonkeyPatch
) -> list[bool]:
    if not on_postgres():
        return list(
            await asyncio.gather(
                _bridge(engine).revive_dead_letter(case.drive),
                _bridge(engine).revive_dead_letter(case.drive),
            )
        )
    original = queue_bridge._locked_run
    first_locked = asyncio.Event()
    release_first = asyncio.Event()
    calls = 0

    async def controlled_lock(
        session: AsyncSession, run_id: str
    ) -> AutopilotRun | None:
        nonlocal calls
        calls += 1
        call = calls
        run = await original(session, run_id)
        if call == 1:
            first_locked.set()
            await release_first.wait()
        return run

    monkeypatch.setattr(queue_bridge, "_locked_run", controlled_lock)
    first = asyncio.create_task(_bridge(engine).revive_dead_letter(case.drive))
    await asyncio.wait_for(first_locked.wait(), 5)
    second = asyncio.create_task(_bridge(engine).revive_dead_letter(case.drive))
    await asyncio.sleep(0.2)
    try:
        assert not first.done()
        assert not second.done()
        release_first.set()
        return list(await asyncio.wait_for(asyncio.gather(first, second), 10))
    finally:
        release_first.set()
        await asyncio.gather(first, second, return_exceptions=True)


async def _owner_race(engine: AsyncEngine, case: _RaceCase) -> tuple[bool, list[str]]:
    if not on_postgres():
        scan_result, said = await asyncio.gather(
            _bridge(engine).revive_dead_letter(case.drive),
            _tap_retry(engine, UUID(case.run_id), 778),
        )
        return scan_result, said
    blocker = _sessions(engine)()
    scan: asyncio.Task[bool] | None = None
    owner: asyncio.Task[list[str]] | None = None
    try:
        result = await blocker.execute(
            select(AutopilotRunModel.id)
            .where(AutopilotRunModel.id == UUID(case.run_id))
            .with_for_update()
        )
        assert result.scalar_one_or_none() is not None
        scan = asyncio.create_task(_bridge(engine).revive_dead_letter(case.drive))
        owner = asyncio.create_task(_tap_retry(engine, UUID(case.run_id), 779))
        await asyncio.sleep(0.2)
        assert not scan.done()
        assert not owner.done()
        await blocker.commit()
        return await asyncio.wait_for(asyncio.gather(scan, owner), 10)
    finally:
        await blocker.close()
        if scan is not None and owner is not None:
            await asyncio.gather(scan, owner, return_exceptions=True)


async def _assert_events(
    engine: AsyncEngine, case: _RaceCase, owner_revived: int
) -> None:
    expected: Counter[str] = Counter()
    if case.state is _S.ESCALATED:
        expected[EVENT_TYPE_STATE_CHANGED] = 1
    if owner_revived:
        expected[AUDIT_CAROUSEL_REPROCESS] = 1
    async with _sessions(engine)() as session:
        audit_rows = (
            await session.execute(
                select(WorkflowAuditLogModel.event_id, WorkflowAuditLogModel.event_type)
            )
        ).all()
        outbox_rows = (
            await session.execute(
                select(EventOutboxModel.event_id, EventOutboxModel.event_type)
            )
        ).all()
    audit_pairs = {(row.event_id, row.event_type) for row in audit_rows}
    outbox_pairs = {(row.event_id, row.event_type) for row in outbox_rows}
    assert audit_pairs == outbox_pairs
    assert Counter(row.event_type for row in audit_rows) == expected


async def _assert_final(
    engine: AsyncEngine, case: _RaceCase, owner_revived: int = 0
) -> None:
    async with _sessions(engine)() as session:
        run = await session.get(AutopilotRunModel, UUID(case.run_id))
        dead = await session.get(GenerationRunModel, case.dead_id)
        assert run is not None
        assert dead is not None
        same_theme = await session.scalar(
            select(func.count())
            .select_from(AutopilotRunModel)
            .where(AutopilotRunModel.topic_candidate_id == run.topic_candidate_id)
        )
        replacements = await session.scalar(
            select(func.count())
            .select_from(AutopilotRunModel)
            .where(
                AutopilotRunModel.topic_candidate_id == run.topic_candidate_id,
                AutopilotRunModel.id != run.id,
                AutopilotRunModel.state == _S.QUEUED.value,
            )
        )
        active = await session.scalar(
            select(func.count())
            .select_from(GenerationRunModel)
            .where(
                GenerationRunModel.autopilot_run_id == case.run_id,
                GenerationRunModel.status.in_(ACTIVE_STATUSES),
            )
        )
    if case.state is _S.ESCALATED:
        assert run.state == _S.GENERATING.value
        assert (int(same_theme or 0), int(replacements or 0)) == (1, 0)
        assert (dead.status, int(active or 0)) == ("queued", 1)
        await _assert_events(engine, case, owner_revived)
        return
    assert run.state == _S.FAILED.value
    assert (int(same_theme or 0), int(replacements or 0)) == (2, 1)
    assert (dead.status, int(active or 0)) == ("dead_letter", 0)
    await _assert_events(engine, case, owner_revived)


@pytest.mark.parametrize("state", [_S.ESCALATED, _S.FAILED])
async def test_forced_concurrent_scans_revive_only_once(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, state: _S
) -> None:
    """Scenario: Concurrent recovery and owner retry revive only once"""
    case = await _setup_case(engine, state)
    results = await _scan_race(engine, case, monkeypatch)
    assert sorted(results) == [False, True]
    await _assert_final(engine, case)


@pytest.mark.parametrize("state", [_S.ESCALATED, _S.FAILED])
async def test_forced_owner_retry_and_scan_revive_only_once(
    engine: AsyncEngine, state: _S
) -> None:
    """Scenario: Concurrent recovery and owner retry revive only once"""
    case = await _setup_case(engine, state)
    scan_result, said = await _owner_race(engine, case)
    owner_revived = int(said[-1].startswith("🔁 De volta à fila"))
    assert int(scan_result) + owner_revived == 1
    await _assert_final(engine, case, owner_revived)
