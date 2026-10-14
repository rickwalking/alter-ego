"""Publish claims never take over a possibly-published container (AE-0348 QA r2 R4).

Gherkin: tests/features/autopilot_instagram_publish.feature
  Scenario: A stale publish claim is not taken over while Graph may still run
  Scenario: A manual publish crash after the container reuses that container
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.constants import CONTAINER_REUSE_HOURS
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.publish import SaveContainerCommand
from rag_backend.modules.autopilot.domain.publish_claims import (
    ManualClaim,
    ManualContainer,
    RunClaim,
)
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.infrastructure.publish_claims import (
    SqlPublishClaims,
)
from rag_backend.modules.autopilot.recovery_constants import (
    MANUAL_CLAIM_STALE_MINUTES,
    MANUAL_STATE_FAILED,
)
from tests.integration.test_autopilot_qa_r1 import _carousel, _run_in

_NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
_STALE = _NOW - timedelta(minutes=MANUAL_CLAIM_STALE_MINUTES)
_LONG_AGO = _STALE - timedelta(minutes=1)


async def _stale_claim_on(db: AsyncSession, run_id: UUID) -> None:
    await db.execute(
        update(AutopilotRunModel)
        .where(AutopilotRunModel.id == run_id)
        .values(publish_claimed_at=_LONG_AGO)
    )
    await db.commit()


# Scenario: A stale publish claim is not taken over while Graph may still run
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("container_age", "taken_over"),
    [
        (None, True),
        (timedelta(hours=1), False),
        (timedelta(hours=CONTAINER_REUSE_HOURS + 1), True),
    ],
)
async def test_stale_claim_takeover_waits_for_an_unknown_fresh_container(
    db_session: AsyncSession,
    container_age: timedelta | None,
    taken_over: bool,
) -> None:
    repo, run = await _run_in(db_session, AutopilotRunState.PUBLISHING)
    if container_age is not None:
        await repo.save_container(
            SaveContainerCommand(
                run_id=run.run_id,
                container_id="container-1",
                created_at=_NOW - container_age,
            )
        )
    await _stale_claim_on(db_session, run.run_id)
    claims = SqlPublishClaims(db_session)

    won = await claims.claim_run(
        RunClaim(run_id=run.run_id, now=_NOW, stale_before=_STALE)
    )

    assert won is taken_over


@pytest.mark.asyncio
async def test_a_released_claim_with_a_fresh_container_can_be_resumed(
    db_session: AsyncSession,
) -> None:
    repo, run = await _run_in(db_session, AutopilotRunState.PUBLISHING)
    await repo.save_container(
        SaveContainerCommand(
            run_id=run.run_id, container_id="container-1", created_at=_NOW
        )
    )
    claims = SqlPublishClaims(db_session)

    won = await claims.claim_run(
        RunClaim(run_id=run.run_id, now=_NOW, stale_before=_STALE)
    )

    assert won is True


# Scenario: A run held by a dead worker's container is resolved by its status
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("claimed_at", "taken_over"),
    [(_LONG_AGO, True), (_NOW, False), (None, True)],
)
async def test_held_takeover_only_replaces_a_stale_or_empty_claim(
    db_session: AsyncSession,
    claimed_at: datetime | None,
    taken_over: bool,
) -> None:
    repo, run = await _run_in(db_session, AutopilotRunState.PUBLISHING)
    await repo.save_container(
        SaveContainerCommand(
            run_id=run.run_id, container_id="container-1", created_at=_NOW
        )
    )
    await db_session.execute(
        update(AutopilotRunModel)
        .where(AutopilotRunModel.id == run.run_id)
        .values(publish_claimed_at=claimed_at)
    )
    await db_session.commit()
    claims = SqlPublishClaims(db_session)
    claim = RunClaim(run_id=run.run_id, now=_NOW, stale_before=_STALE)

    won = await claims.take_over_held(claim)

    assert won is taken_over


# Scenario: A manual publish crash after the container reuses that container
@pytest.mark.asyncio
async def test_manual_container_is_persisted_and_blocks_stale_takeover(
    db_session: AsyncSession,
) -> None:
    project_id = await _carousel(db_session)
    claims = SqlPublishClaims(db_session)
    first = ManualClaim(project_id=project_id, now=_LONG_AGO, stale_before=_STALE)
    assert await claims.claim_manual(first) is True
    await claims.save_manual_container(
        ManualContainer(
            project_id=project_id, container_id="manual-container", created_at=_NOW
        )
    )

    record = await claims.manual_record(project_id)
    retry = ManualClaim(project_id=project_id, now=_NOW, stale_before=_STALE)
    refused = await claims.claim_manual(retry)
    assert record is not None
    await claims.finish_manual(replace(record, state=MANUAL_STATE_FAILED))
    after_failure = await claims.claim_manual(retry)
    kept = await claims.manual_record(project_id)

    assert record.ig_container_id == "manual-container"
    assert refused is False
    assert after_failure is True
    assert kept is not None
    assert kept.ig_container_id == "manual-container"
