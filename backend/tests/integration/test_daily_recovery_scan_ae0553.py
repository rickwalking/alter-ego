"""Atomic daily revival and its scan/owner races on a real database.

Feature: backend/tests/features/daily_recovery_scan_ae0553.feature
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
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
from tests.integration.test_daily_recovery_scan_ae0524 import (
    _NOW,
    _autopilot_run,
    _bridge,
    _generation,
    _generation_row,
    _run_state,
    _scan,
    _sessions,
    engine,
)
from tests.integration.test_queue_retry_ae0523 import _parked, _tap_retry

__all__ = ["engine"]

_S = AutopilotRunState
_DEAD = "queue_dead_letter:run_budget_exhausted"


class _DayClock:
    def __init__(self, day: int) -> None:
        self._day = day

    def now(self) -> datetime:
        return _NOW + timedelta(days=self._day)


def _scan_on(engine: AsyncEngine, day: int) -> DailyRecoveryScan:
    return DailyRecoveryScan(
        DailyScanDependencies(
            store=SqlRecoveryStore(_sessions(engine)),
            autopilot=_bridge(engine),
            clock=_DayClock(day),
        )
    )


async def test_a_failed_revive_does_not_consume_the_recovery_attempt(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: A failed revive does not consume the recovery attempt"""
    from rag_backend.modules.autopilot import queue_bridge

    run = await _autopilot_run(engine, _S.ESCALATED, _DEAD, timedelta(hours=20))
    dead = await _generation(
        engine, run, "dead_letter", ("run_budget_exhausted", timedelta(hours=20))
    )
    original = queue_bridge._revive_once
    calls = 0

    async def fail_once(session: AsyncSession, autopilot_run: AutopilotRun) -> bool:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("database unavailable")
        return await original(session, autopilot_run)

    monkeypatch.setattr(queue_bridge, "_revive_once", fail_once)
    first = await _scan_on(engine, 0).run_once()
    row = await _generation_row(engine, dead)
    assert first.recovered == 0
    assert row.status == "dead_letter"
    assert row.payload.get("recovery_attempt") is not True
    assert await _run_state(engine, run) == (_S.ESCALATED.value, _DEAD)
    second = await _scan_on(engine, 1).run_once()
    row = await _generation_row(engine, dead)
    assert second.recovered == 1
    assert row.status == "queued"
    assert row.payload["recovery_attempt"] is True
    assert await _run_state(engine, run) == (
        _S.GENERATING.value,
        REASON_DAILY_RECOVERY,
    )
    assert calls == 2


async def test_concurrent_scans_revive_only_once(engine: AsyncEngine) -> None:
    """Scenario: Concurrent recovery and owner retry revive only once"""
    run = await _autopilot_run(engine, _S.ESCALATED, _DEAD, timedelta(hours=5))
    dead = await _generation(
        engine, run, "dead_letter", ("transient", timedelta(hours=5))
    )
    first, second = await asyncio.gather(
        _scan(engine).run_once(), _scan(engine).run_once()
    )
    assert first.recovered + second.recovered == 1
    assert (await _generation_row(engine, dead)).status == "queued"
    assert (await _run_state(engine, run))[0] == _S.GENERATING.value


async def test_concurrent_owner_retry_and_scan_revive_only_once(
    engine: AsyncEngine,
) -> None:
    """Scenario: Concurrent recovery and owner retry revive only once"""
    run, dead = await _parked(engine)
    report, said = await asyncio.gather(
        _scan(engine).run_once(), _tap_retry(engine, run, 901)
    )
    owner_revived = int(said[-1].startswith("🔁 De volta à fila"))
    assert report.recovered + owner_revived == 1
    async with _sessions(engine)() as session:
        stored_run = await session.get(AutopilotRunModel, run)
        stored_generation = await session.get(GenerationRunModel, dead)
    assert stored_run is not None
    assert stored_generation is not None
    assert stored_run.state == _S.GENERATING.value
    assert stored_generation.status == "queued"
