"""Unit tests for WorkflowFailureAlertService.

Feature: phase5_migration_launch.feature — MON-002
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services.workflow_failure_alert_service import (
    WorkflowFailureAlertService,
)
from rag_backend.domain.constants.carousel import CAROUSEL_STATUS_FAILED
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_RESEARCH,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.constants.workflow_alerts import (
    NOTIFICATION_TYPE_WORKFLOW_FAILURE,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.notification import NotificationModel
from rag_backend.infrastructure.database.models.user import UserModel


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        admin = UserModel(
            id="admin-id",
            email="admin@test.com",
            full_name="Admin",
            hashed_password="hash",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        yield db
    await engine.dispose()


@pytest.mark.asyncio
class TestWorkflowFailureAlertService:
    async def test_alerts_on_recent_failed_carousel(
        self, session: AsyncSession
    ) -> None:
        now = datetime.now(UTC)
        project = CarouselProjectModel(
            id=str(uuid.uuid4()),
            topic="Test",
            audience="Devs",
            niche="Tech",
            status=CAROUSEL_STATUS_FAILED,
            error_message="Generation timeout",
            updated_at=now,
            created_at=now,
        )
        session.add(project)
        await session.commit()

        count = await WorkflowFailureAlertService().check_and_alert(session)
        await session.commit()

        assert count >= 1
        result = await session.execute(
            select(NotificationModel).where(
                NotificationModel.notification_type
                == NOTIFICATION_TYPE_WORKFLOW_FAILURE
            )
        )
        notifications = list(result.scalars().all())
        assert len(notifications) >= 1

    async def test_no_duplicate_alerts_on_second_tick(
        self, session: AsyncSession
    ) -> None:
        now = datetime.now(UTC)
        project = CarouselProjectModel(
            id=str(uuid.uuid4()),
            topic="Test",
            audience="Devs",
            niche="Tech",
            status=CAROUSEL_STATUS_FAILED,
            error_message="Generation timeout",
            updated_at=now,
            created_at=now,
        )
        session.add(project)
        await session.commit()

        service = WorkflowFailureAlertService()
        first = await service.check_and_alert(session)
        await session.commit()
        second = await service.check_and_alert(session)
        await session.commit()

        assert first >= 1
        assert second == 0

    async def test_no_alert_when_no_recent_failures(
        self, session: AsyncSession
    ) -> None:
        old = datetime.now(UTC) - timedelta(hours=5)
        project = CarouselProjectModel(
            id=str(uuid.uuid4()),
            topic="Old fail",
            audience="Devs",
            niche="Tech",
            status=CAROUSEL_STATUS_FAILED,
            error_message="Old error",
            updated_at=old,
            created_at=old,
        )
        session.add(project)
        await session.commit()

        count = await WorkflowFailureAlertService().check_and_alert(session)
        assert count == 0

    async def test_alerts_on_stuck_workflow(self, session: AsyncSession) -> None:
        stale = datetime.now(UTC) - timedelta(hours=72)
        project = CarouselProjectModel(
            id=str(uuid.uuid4()),
            topic="Stuck",
            audience="Devs",
            niche="Tech",
            status=CAROUSEL_STATUS_FAILED,
            current_phase=PHASE_RESEARCH,
            phase_status="in_progress",
            updated_at=stale,
            created_at=stale,
        )
        session.add(project)
        await session.commit()

        count = await WorkflowFailureAlertService().check_and_alert(session)
        await session.commit()

        assert count >= 1

    async def test_alerts_on_high_failure_rate(self, session: AsyncSession) -> None:
        now = datetime.now(UTC)
        for index in range(4):
            session.add(
                CarouselProjectModel(
                    id=str(uuid.uuid4()),
                    topic=f"Fail {index}",
                    audience="Devs",
                    niche="Tech",
                    status=CAROUSEL_STATUS_FAILED,
                    updated_at=now,
                    created_at=now,
                )
            )
        session.add(
            CarouselProjectModel(
                id=str(uuid.uuid4()),
                topic="Ok",
                audience="Devs",
                niche="Tech",
                status="completed",
                updated_at=now,
                created_at=now,
            )
        )
        await session.commit()

        count = await WorkflowFailureAlertService().check_and_alert(session)
        await session.commit()

        assert count >= 1

    async def test_in_progress_excluded_from_stuck_alerts(
        self, session: AsyncSession
    ) -> None:
        """AE-0026: Projects with phase_status in_progress are excluded from stuck detection."""
        recent = datetime.now(UTC) - timedelta(minutes=5)
        project = CarouselProjectModel(
            id=str(uuid.uuid4()),
            topic="Active resume",
            audience="Devs",
            niche="Tech",
            status="draft",
            current_phase=PHASE_RESEARCH,
            phase_status=PHASE_STATUS_IN_PROGRESS,
            updated_at=recent,
            created_at=recent,
        )
        session.add(project)
        await session.commit()

        count = await WorkflowFailureAlertService().check_and_alert(session)
        assert count == 0

    async def test_stale_in_progress_alerts_after_ttl(
        self, session: AsyncSession
    ) -> None:
        """AE-0026: Stale in_progress projects older than 30 min trigger stuck alert."""
        stale = datetime.now(UTC) - timedelta(hours=1)
        project = CarouselProjectModel(
            id=str(uuid.uuid4()),
            topic="Stuck resume",
            audience="Devs",
            niche="Tech",
            status="draft",
            current_phase=PHASE_RESEARCH,
            phase_status=PHASE_STATUS_IN_PROGRESS,
            updated_at=stale,
            created_at=stale,
        )
        session.add(project)
        await session.commit()

        count = await WorkflowFailureAlertService().check_and_alert(session)
        await session.commit()

        assert count >= 1
