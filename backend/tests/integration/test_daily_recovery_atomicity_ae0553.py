"""Post-write rollback for every daily-recovery revive branch.

Feature: backend/tests/features/daily_recovery_scan_ae0553.feature
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)
from rag_backend.modules.autopilot.application.run_revive import ReviveDependencies
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.generation_queue.domain.recovery import ParkedDrive
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from tests.integration.test_daily_recovery_scan_ae0524 import (
    _autopilot_run,
    _bridge,
    _generation,
    _sessions,
    engine,
)

__all__ = ["engine"]

_S = AutopilotRunState
_DEAD = "queue_dead_letter:run_budget_exhausted"


async def _event_counts(engine: AsyncEngine) -> tuple[int, int]:
    async with _sessions(engine)() as session:
        audit = await session.scalar(
            select(func.count()).select_from(WorkflowAuditLogModel)
        )
        outbox = await session.scalar(
            select(func.count()).select_from(EventOutboxModel)
        )
    return int(audit or 0), int(outbox or 0)


@pytest.mark.parametrize("state", [_S.ESCALATED, _S.FAILED])
async def test_post_write_failure_rolls_back_every_revive_write(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, state: _S
) -> None:
    """Scenario: A failed revive does not consume the recovery attempt"""
    from rag_backend.modules.autopilot import queue_bridge

    run_id = await _autopilot_run(engine, state, _DEAD, timedelta(hours=5))
    dead_id = await _generation(
        engine, run_id, "dead_letter", ("transient", timedelta(hours=5))
    )
    before = await _event_counts(engine)
    original = queue_bridge.revive
    entered = 0

    async def fail_after_writes(
        deps: ReviveDependencies, run: AutopilotRun, reason: str
    ) -> None:
        nonlocal entered
        queued_id = await original(deps, run, reason)
        assert queued_id is not None
        entered += 1
        raise RuntimeError("after partial revive writes")

    monkeypatch.setattr(queue_bridge, "revive", fail_after_writes)
    drive = ParkedDrive(generation_run_id=dead_id, autopilot_run_id=run_id)
    with pytest.raises(RuntimeError, match="after partial revive writes"):
        await _bridge(engine).revive_dead_letter(drive)
    assert entered == 1
    async with _sessions(engine)() as session:
        run = await session.get(AutopilotRunModel, UUID(run_id))
        dead = await session.get(GenerationRunModel, dead_id)
        assert run is not None
        assert dead is not None
        same_theme = await session.scalar(
            select(func.count())
            .select_from(AutopilotRunModel)
            .where(AutopilotRunModel.topic_candidate_id == run.topic_candidate_id)
        )
    assert (run.state, run.state_reason) == (state.value, _DEAD)
    assert run.telegram_message_ids == []
    assert int(same_theme or 0) == 1
    assert dead.status == "dead_letter"
    assert dead.payload.get("recovery_attempt") is not True
    assert dead.phase_attempts == {"content": 2}
    assert dead.finished_at is not None
    assert await _event_counts(engine) == before
