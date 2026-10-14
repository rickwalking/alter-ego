"""Escalated wake scan rotates by last check (AE-0348 QA r2 R1).

Gherkin: tests/features/autopilot_runner.feature
  Scenario: A fixed escalation wakes even behind five abandoned ones
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.recovery import EscalatedScan, WakeCheck
from rag_backend.modules.autopilot.infrastructure.run_recovery_store import (
    SqlRunRecoveryStore,
)
from rag_backend.modules.autopilot.recovery_constants import ESCALATED_SCAN_LIMIT
from tests.integration.test_autopilot_qa_r1 import _run_in, _stored

_NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


# Scenario: A fixed escalation wakes even behind five abandoned ones
@pytest.mark.asyncio
async def test_checked_runs_go_to_the_back_of_the_scan(
    db_session: AsyncSession,
) -> None:
    created = [
        await _run_in(db_session, AutopilotRunState.ESCALATED)
        for _ in range(ESCALATED_SCAN_LIMIT + 1)
    ]
    repo = created[0][0]
    store = SqlRunRecoveryStore(db_session)
    scan = EscalatedScan(limit=ESCALATED_SCAN_LIMIT)

    first = await store.escalated_for_check(scan)
    before = {run.run_id: (await _stored(repo, run.run_id)).updated_at for run in first}
    for offset, run in enumerate(first):
        at = _NOW + timedelta(seconds=offset)
        await store.mark_checked(WakeCheck(run_id=run.run_id, at=at))
    second = await store.escalated_for_check(scan)

    all_ids = {run.run_id for _repo, run in created}
    [unchecked] = all_ids - {run.run_id for run in first}
    assert len(first) == ESCALATED_SCAN_LIMIT
    assert second[0].run_id == unchecked
    assert second[1].run_id == first[0].run_id
    for run in first:
        assert (await _stored(repo, run.run_id)).updated_at == before[run.run_id]


@pytest.mark.asyncio
async def test_only_escalated_runs_are_scanned(db_session: AsyncSession) -> None:
    await _run_in(db_session, AutopilotRunState.AWAITING_OWNER)
    _repo, escalated = await _run_in(db_session, AutopilotRunState.ESCALATED)

    found = await SqlRunRecoveryStore(db_session).escalated_for_check(
        EscalatedScan(limit=ESCALATED_SCAN_LIMIT)
    )

    assert [run.run_id for run in found] == [escalated.run_id]
