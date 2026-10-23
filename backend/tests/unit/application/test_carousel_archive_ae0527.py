"""Archived carousels raise no alerts; idle carousels archive themselves."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services.workflow_failure_alert_service import (
    WorkflowFailureAlertService,
)
from rag_backend.application.workers.workflow_workers import (
    _auto_archive,
    _TickCollaborators,
)
from rag_backend.domain.constants.carousel import CAROUSEL_STATUS_FAILED
from rag_backend.domain.constants.carousel_archive import (
    CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_PUBLISHED,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.database.carousel_auto_archiver import (
    CarouselIdleArchiver,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.notification import NotificationModel
from rag_backend.infrastructure.database.models.user import UserModel

STALE_SECONDS = 180
_NOW = datetime.now(UTC)
_IDLE = _NOW - timedelta(days=CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS + 1)
_ARCHIVER = CarouselIdleArchiver(STALE_SECONDS, clock=lambda: _NOW)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        db.add(
            UserModel(
                id="admin-id",
                email="admin@test.com",
                full_name="Admin",
                hashed_password="hash",
                role="admin",
                is_active=True,
            )
        )
        await db.commit()
        yield db
    db_config.c_engine = None
    await engine.dispose()


def _project(
    updated_at: datetime,
    *,
    phase: str | None = PHASE_RESEARCH,
    phase_status: str | None = PHASE_STATUS_AWAITING_HUMAN,
    archived_at: datetime | None = None,
    status: str = "draft",
    run_heartbeat_at: datetime | None = None,
) -> CarouselProjectModel:
    return CarouselProjectModel(
        id=str(uuid.uuid4()),
        topic="Idle",
        audience="Devs",
        niche="Tech",
        status=status,
        current_phase=phase,
        phase_status=phase_status,
        archived_at=archived_at,
        run_heartbeat_at=run_heartbeat_at,
        updated_at=updated_at,
        created_at=updated_at,
    )


async def _notifications(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(NotificationModel))
    return int(result.scalar_one())


async def _archived(db: AsyncSession, project_id: str) -> bool:
    project = await db.get(CarouselProjectModel, project_id)
    assert project is not None
    await db.refresh(project)
    return project.archived_at is not None


@pytest.mark.asyncio
class TestArchivedCarouselsRaiseNoAlerts:
    async def test_archived_stuck_and_failed_carousels_raise_no_alert(
        self, session: AsyncSession
    ) -> None:
        """Scenario: An archived carousel raises no alerts"""
        session.add(_project(_IDLE, archived_at=_IDLE))
        session.add(
            _project(
                _NOW - timedelta(hours=1),
                phase_status=PHASE_STATUS_IN_PROGRESS,
                archived_at=_NOW,
            )
        )
        session.add(
            _project(
                _NOW, phase_status=None, status=CAROUSEL_STATUS_FAILED, archived_at=_NOW
            )
        )
        await session.commit()

        count = await WorkflowFailureAlertService().check_and_alert(session)
        await session.commit()

        assert count == 0
        assert await _notifications(session) == 0

    async def test_the_same_carousels_alert_when_not_archived(
        self, session: AsyncSession
    ) -> None:
        """Scenario: An archived carousel raises no alerts"""
        session.add(_project(_IDLE))
        session.add(_project(_NOW, phase_status=None, status=CAROUSEL_STATUS_FAILED))
        await session.commit()

        count = await WorkflowFailureAlertService().check_and_alert(session)
        await session.commit()

        assert count == 2


@pytest.mark.asyncio
class TestCarouselIdleArchiver:
    async def test_idle_carousel_is_archived(self, session: AsyncSession) -> None:
        """Scenario: An idle carousel is archived automatically"""
        idle = _project(_IDLE)
        no_phase = _project(_IDLE, phase=None, phase_status=None)
        session.add_all([idle, no_phase])
        await session.commit()

        archived = await _ARCHIVER.archive_idle(
            session, CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS
        )
        await session.commit()

        assert archived == 2
        assert await _archived(session, str(idle.id))
        assert await _archived(session, str(no_phase.id))
        stored = await session.get(CarouselProjectModel, str(idle.id))
        assert stored is not None
        assert stored.current_phase == PHASE_RESEARCH
        assert stored.phase_status == PHASE_STATUS_AWAITING_HUMAN

    async def test_active_published_and_in_progress_are_kept(
        self, session: AsyncSession
    ) -> None:
        """Scenario: Active, published and in-progress carousels are not auto-archived"""
        recent = _project(_NOW - timedelta(days=CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS - 1))
        published = _project(_IDLE, phase=PHASE_PUBLISHED)
        running = _project(
            _IDLE, phase_status=PHASE_STATUS_IN_PROGRESS, run_heartbeat_at=_NOW
        )
        session.add_all([recent, published, running])
        await session.commit()

        archived = await _ARCHIVER.archive_idle(
            session, CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS
        )

        assert archived == 0
        for project in (recent, published, running):
            assert not await _archived(session, str(project.id))

    async def test_an_archived_carousel_is_not_archived_again(
        self, session: AsyncSession
    ) -> None:
        """Scenario: Archiving twice keeps the first archive time"""
        session.add(_project(_IDLE, archived_at=_IDLE))
        await session.commit()

        archived = await _ARCHIVER.archive_idle(
            session, CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS
        )

        assert archived == 0


def _collaborators(archiver: AsyncMock | None) -> _TickCollaborators:
    return _TickCollaborators(
        notifications=AsyncMock(),
        alerts=AsyncMock(),
        auto_rejector=AsyncMock(),
        stale_run_reaper=None,
        drift_reconciler=None,
        republish_sweeper=None,
        carousel_auto_archiver=archiver,
    )


@pytest.mark.asyncio
class TestWorkerAutoArchive:
    async def test_the_tick_archives_with_the_configured_days(self) -> None:
        """Scenario: An idle carousel is archived automatically"""
        archiver = AsyncMock()
        archiver.archive_idle = AsyncMock(return_value=3)
        db = AsyncMock()

        archived = await _auto_archive(
            Settings(carousel_auto_archive_days=45), db, _collaborators(archiver)
        )

        assert archived == 3
        archiver.archive_idle.assert_awaited_once_with(db, 45)

    async def test_zero_days_turns_auto_archive_off(self) -> None:
        """Scenario: Auto-archive can be turned off"""
        archiver = AsyncMock()

        archived = await _auto_archive(
            Settings(carousel_auto_archive_days=0),
            AsyncMock(),
            _collaborators(archiver),
        )

        assert archived == 0
        archiver.archive_idle.assert_not_awaited()

    async def test_no_archiver_archives_nothing(self) -> None:
        """Scenario: Auto-archive can be turned off"""
        archived = await _auto_archive(Settings(), AsyncMock(), _collaborators(None))

        assert archived == 0


def test_the_default_window_is_30_days() -> None:
    """Scenario: An idle carousel is archived automatically"""
    assert Settings().carousel_auto_archive_days == 30
