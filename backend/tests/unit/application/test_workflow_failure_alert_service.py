"""Unit tests for WorkflowFailureAlertService.

Feature: phase5_migration_launch.feature — MON-002
Feature: stuck_workflow_alerts.feature
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services import workflow_failure_alert_service
from rag_backend.application.services.workflow_failure_alert_service import (
    WorkflowFailureAlertService,
)
from rag_backend.domain.constants.carousel import CAROUSEL_STATUS_FAILED
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_OUTLINE,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.constants.workflow_alerts import (
    ALERT_TYPE_STUCK_WORKFLOW,
    NOTIFICATION_TYPE_WORKFLOW_FAILURE,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.notification import NotificationModel
from rag_backend.infrastructure.database.models.user import UserModel


STUCK_PROJECT_COUNT = 15
SECOND_ADMIN_ID = "admin-2-id"


class _RecordingLogger:
    """Stands in for the module logger and keeps every warning's fields."""

    def __init__(self) -> None:
        self.warnings: list[dict[str, object]] = []

    def warning(self, event: str, **fields: object) -> None:
        self.warnings.append({"event": event, **fields})

    def error(self, event: str, **fields: object) -> None:
        del event, fields

    def stuck_lines(self) -> list[dict[str, object]]:
        return [
            line
            for line in self.warnings
            if line.get("alert_type") == ALERT_TYPE_STUCK_WORKFLOW
        ]


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> _RecordingLogger:
    recorder = _RecordingLogger()
    monkeypatch.setattr(workflow_failure_alert_service, "logger", recorder)
    return recorder


def _stuck_project(updated_at: datetime) -> CarouselProjectModel:
    return CarouselProjectModel(
        id=str(uuid.uuid4()),
        topic="Stuck",
        audience="Devs",
        niche="Tech",
        status="draft",
        current_phase=PHASE_RESEARCH,
        phase_status=PHASE_STATUS_AWAITING_HUMAN,
        updated_at=updated_at,
        created_at=updated_at,
    )


async def _notification_count(db: AsyncSession, project_id: str) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(NotificationModel)
        .where(NotificationModel.content_id == project_id)
    )
    return int(result.scalar_one())


async def _backdate_notifications(db: AsyncSession, created_at: datetime) -> None:
    result = await db.execute(select(NotificationModel))
    for notification in result.scalars().all():
        notification.created_at = created_at
    await db.commit()


async def _add_second_admin(db: AsyncSession) -> None:
    db.add(
        UserModel(
            id=SECOND_ADMIN_ID,
            email="admin2@test.com",
            full_name="Admin Two",
            hashed_password="hash",
            role="admin",
            is_active=True,
        )
    )
    await db.commit()


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
        """Projects with phase_status in_progress are excluded from stuck detection."""
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
        """Stale in_progress projects older than 30 min trigger stuck alert."""
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


@pytest.mark.asyncio
class TestStuckWorkflowEpisodes:
    """Stuck alerts are deduplicated per stuck episode, not per hour."""

    async def test_stuck_project_alerts_once_per_episode(
        self, session: AsyncSession, recorded: _RecordingLogger
    ) -> None:
        """Scenario: A stuck project alerts once per stuck episode."""
        await _add_second_admin(session)
        now = datetime.now(UTC)
        project = _stuck_project(now - timedelta(hours=72))
        session.add(project)
        await session.commit()
        service = WorkflowFailureAlertService()

        first = await service.check_and_alert(session)
        await session.commit()
        assert first == 1
        assert len(recorded.stuck_lines()) == 1
        assert await _notification_count(session, project.id) == 2

        await _backdate_notifications(session, now - timedelta(hours=3))
        later = [await service.check_and_alert(session) for _ in range(3)]
        await session.commit()

        assert later == [0, 0, 0]
        assert len(recorded.stuck_lines()) == 1
        assert await _notification_count(session, project.id) == 2

    async def test_project_stuck_again_after_moving_alerts_again(
        self, session: AsyncSession, recorded: _RecordingLogger
    ) -> None:
        """Scenario: A project that moves and gets stuck again alerts again."""
        now = datetime.now(UTC)
        project = _stuck_project(now - timedelta(hours=120))
        session.add(project)
        await session.commit()
        service = WorkflowFailureAlertService()
        assert await service.check_and_alert(session) == 1
        await session.commit()
        await _backdate_notifications(session, now - timedelta(hours=70))

        project.current_phase = PHASE_OUTLINE
        project.updated_at = now - timedelta(hours=50)
        await session.commit()

        assert await service.check_and_alert(session) == 1
        await session.commit()
        assert len(recorded.stuck_lines()) == 2
        assert await _notification_count(session, project.id) == 2

    async def test_already_alerted_stuck_projects_keep_the_log_quiet(
        self, session: AsyncSession, recorded: _RecordingLogger
    ) -> None:
        """Scenario: Already alerted stuck projects keep the log quiet."""
        now = datetime.now(UTC)
        for _ in range(STUCK_PROJECT_COUNT):
            session.add(_stuck_project(now - timedelta(hours=72)))
        await session.commit()
        service = WorkflowFailureAlertService()
        assert await service.check_and_alert(session) == STUCK_PROJECT_COUNT
        await session.commit()
        await _backdate_notifications(session, now - timedelta(hours=2))
        recorded.warnings.clear()

        assert await service.check_and_alert(session) == 0
        assert recorded.warnings == []
