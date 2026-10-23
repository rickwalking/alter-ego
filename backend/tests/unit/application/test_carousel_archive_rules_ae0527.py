"""The archive rules: what may be archived, by the owner or by the idle worker."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel import CAROUSEL_STATUS_DRAFTING
from rag_backend.domain.constants.carousel_archive import (
    ARCHIVE_REFUSED_AUTOPILOT,
    ARCHIVE_REFUSED_IN_PROGRESS,
    ARCHIVE_REFUSED_PUBLISHED,
    CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_PUBLISHED,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.infrastructure.database.carousel_auto_archiver import (
    CarouselIdleArchiver,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models import (
    archivable,
    archive_refusal_of,
    archive_refusals,
    archive_where,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from tests.unit.application.test_carousel_archive_ae0527 import (
    STALE_SECONDS,
    _archived,
    _project,
    session,
)

__all__ = ["session"]

_NOW = datetime.now(UTC)
_IDLE = _NOW - timedelta(days=CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS + 1)
_STALE = _NOW - timedelta(seconds=STALE_SECONDS + 60)
_RUNS = Base.metadata.tables["autopilot_runs"]
_ARCHIVER = CarouselIdleArchiver(STALE_SECONDS, clock=lambda: _NOW)


async def _with_run(db: AsyncSession, project_id: str, state: str) -> None:
    await db.execute(
        insert(_RUNS).values(
            id=uuid.uuid4(),
            carousel_project_id=project_id,
            topic_candidate_id=uuid.uuid4(),
            state=state,
            telegram_message_ids={},
            created_at=_NOW,
        )
    )


async def _seed(db: AsyncSession, **fields: object) -> str:
    project = _project(_IDLE, **fields)
    db.add(project)
    await db.commit()
    return str(project.id)


@pytest.fixture
async def db(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    yield session


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state", ["scheduled", "publishing", "awaiting_owner", "queued"]
)
async def test_an_autopilot_run_still_going_keeps_the_carousel(
    db: AsyncSession, state: str
) -> None:
    """Scenario: A carousel an autopilot run still needs is not auto-archived"""
    project_id = await _seed(db)
    await _with_run(db, project_id, state)
    await db.commit()

    assert await _ARCHIVER.archive_idle(db, CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS) == 0
    assert not await _archived(db, project_id)
    refusal = await archive_refusal_of(db, project_id, (_NOW, STALE_SECONDS))
    assert refusal == ARCHIVE_REFUSED_AUTOPILOT


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["published", "rejected", "expired", "failed"])
async def test_a_finished_autopilot_run_does_not_keep_the_carousel(
    db: AsyncSession, state: str
) -> None:
    """Scenario: An idle carousel is archived automatically"""
    project_id = await _seed(db)
    await _with_run(db, project_id, state)
    await db.commit()

    assert await _ARCHIVER.archive_idle(db, CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS) == 1
    assert await _archived(db, project_id)


@pytest.mark.asyncio
async def test_a_live_run_and_a_generating_status_keep_the_carousel(
    db: AsyncSession,
) -> None:
    """Scenario: Active, published and in-progress carousels are not auto-archived"""
    live = await _seed(db, phase_status=PHASE_STATUS_IN_PROGRESS, run_heartbeat_at=_NOW)
    generating = await _seed(db, status=CAROUSEL_STATUS_DRAFTING)

    assert await _ARCHIVER.archive_idle(db, CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS) == 0
    assert not await _archived(db, live)
    assert not await _archived(db, generating)


@pytest.mark.asyncio
async def test_a_phase_stuck_with_a_stale_heartbeat_is_archived(
    db: AsyncSession,
) -> None:
    """Scenario: A phase stuck with a stale heartbeat can be archived"""
    stuck = await _seed(
        db, phase_status=PHASE_STATUS_IN_PROGRESS, run_heartbeat_at=_STALE
    )

    assert await _ARCHIVER.archive_idle(db, CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS) == 1
    assert await _archived(db, stuck)


@pytest.mark.asyncio
async def test_archiving_keeps_updated_at_and_returns_the_ids(db: AsyncSession) -> None:
    """Scenario: An idle carousel is archived automatically"""
    project_id = await _seed(db)

    archived = await archive_where(db, archivable(_NOW, STALE_SECONDS), _NOW)
    await db.commit()

    assert archived == [project_id]
    stored = await db.get(CarouselProjectModel, project_id)
    assert stored is not None
    await db.refresh(stored)
    assert stored.updated_at.replace(tzinfo=UTC) == _IDLE.replace(tzinfo=UTC)


@pytest.mark.asyncio
async def test_the_write_rechecks_the_rules(db: AsyncSession) -> None:
    """Scenario: A run that starts before the write keeps the carousel"""
    project_id = await _seed(db)
    stored = await db.get(CarouselProjectModel, project_id)
    assert stored is not None
    stored.phase_status = PHASE_STATUS_IN_PROGRESS
    await db.commit()

    predicates = [
        CarouselProjectModel.id == project_id,
        *archivable(_NOW, STALE_SECONDS),
    ]
    assert await archive_where(db, predicates, _NOW) == []
    assert not await _archived(db, project_id)


@pytest.mark.asyncio
async def test_refusals_name_the_reason_per_card(db: AsyncSession) -> None:
    """Scenario: A carousel in progress cannot be archived"""
    published = await _seed(db, phase=PHASE_PUBLISHED)
    live = await _seed(db, phase_status=PHASE_STATUS_IN_PROGRESS, run_heartbeat_at=_NOW)
    scheduled = await _seed(db)
    await _with_run(db, scheduled, "scheduled")
    free = await _seed(
        db, phase_status=PHASE_STATUS_IN_PROGRESS, run_heartbeat_at=_STALE
    )
    await db.commit()

    refusals = await archive_refusals(
        db, [published, live, scheduled, free], (_NOW, STALE_SECONDS)
    )

    assert refusals == {
        published: ARCHIVE_REFUSED_PUBLISHED,
        live: ARCHIVE_REFUSED_IN_PROGRESS,
        scheduled: ARCHIVE_REFUSED_AUTOPILOT,
    }
    assert await archive_refusals(db, [], (_NOW, STALE_SECONDS)) == {}
    assert await archive_refusal_of(db, free, (_NOW, STALE_SECONDS)) is None
    assert await archive_refusal_of(db, "missing", (_NOW, STALE_SECONDS)) is None
