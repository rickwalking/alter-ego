"""Unit tests for WorkflowTimeoutRepository (AE-0210).

Feature: tests/features/workflow_never_stuck.feature
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_BRIEF,
    PHASE_PUBLISHED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_PENDING,
    PHASE_STATUS_REJECTED,
)
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_PROJECT,
    EVENT_TYPE_PROJECT_PHASE_CHANGED,
)
from rag_backend.domain.constants.workflow_timeout import AUTO_REJECT_CAROUSEL_STATUS
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)
from rag_backend.infrastructure.database.workflow_timeout_repository import (
    WorkflowTimeoutRepository,
)
from rag_backend.infrastructure.events.memory_event_publisher import (
    MemoryEventPublisher,
)

_TIMEOUT_HOURS = 72


def _service() -> WorkflowTimeoutRepository:
    return WorkflowTimeoutRepository(WorkflowEventService(MemoryEventPublisher()))


async def _add_project(
    db: AsyncSession,
    *,
    phase: str,
    phase_status: str,
    updated_at: datetime,
) -> str:
    project_id = str(uuid.uuid4())
    db.add(
        CarouselProjectModel(
            id=project_id,
            topic="Stuck topic",
            audience="Devs",
            niche="Tech",
            status="draft",
            current_phase=phase,
            phase_status=phase_status,
            updated_at=updated_at,
            created_at=updated_at,
        )
    )
    await db.commit()
    return project_id


@pytest.mark.asyncio
class TestWorkflowTimeoutRepository:
    # Scenario: Workflow past the timeout is auto-rejected
    async def test_past_timeout_pending_is_auto_rejected(self, test_engine) -> None:
        factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        stale = datetime.now(UTC) - timedelta(hours=_TIMEOUT_HOURS + 1)
        async with factory() as db:
            project_id = await _add_project(
                db,
                phase=PHASE_BRIEF,
                phase_status=PHASE_STATUS_PENDING,
                updated_at=stale,
            )

            rejected = await _service().auto_reject_stuck(db, _TIMEOUT_HOURS)
            await db.commit()

            assert rejected == 1
            project = await db.get(CarouselProjectModel, project_id)
            assert project is not None
            assert project.phase_status == PHASE_STATUS_REJECTED
            assert project.status == AUTO_REJECT_CAROUSEL_STATUS
            assert project.error_message is not None

            audit = await db.execute(
                select(WorkflowAuditLogModel).where(
                    WorkflowAuditLogModel.aggregate_id == project_id,
                    WorkflowAuditLogModel.aggregate_type == AGGREGATE_TYPE_PROJECT,
                    WorkflowAuditLogModel.event_type
                    == EVENT_TYPE_PROJECT_PHASE_CHANGED,
                )
            )
            assert audit.scalars().first() is not None

    # Scenario: Workflow within the timeout window is left untouched
    async def test_within_window_is_untouched(self, test_engine) -> None:
        factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        recent = datetime.now(UTC) - timedelta(hours=_TIMEOUT_HOURS - 1)
        async with factory() as db:
            project_id = await _add_project(
                db,
                phase=PHASE_BRIEF,
                phase_status=PHASE_STATUS_PENDING,
                updated_at=recent,
            )

            rejected = await _service().auto_reject_stuck(db, _TIMEOUT_HOURS)
            await db.commit()

            assert rejected == 0
            project = await db.get(CarouselProjectModel, project_id)
            assert project is not None
            assert project.phase_status == PHASE_STATUS_PENDING

    # Scenario: In-progress workflow is not auto-rejected
    async def test_in_progress_is_not_rejected(self, test_engine) -> None:
        factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        stale = datetime.now(UTC) - timedelta(hours=_TIMEOUT_HOURS + 5)
        async with factory() as db:
            project_id = await _add_project(
                db,
                phase=PHASE_BRIEF,
                phase_status=PHASE_STATUS_IN_PROGRESS,
                updated_at=stale,
            )

            rejected = await _service().auto_reject_stuck(db, _TIMEOUT_HOURS)
            await db.commit()

            assert rejected == 0
            project = await db.get(CarouselProjectModel, project_id)
            assert project is not None
            assert project.phase_status == PHASE_STATUS_IN_PROGRESS

    async def test_awaiting_human_past_timeout_is_rejected(self, test_engine) -> None:
        factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        stale = datetime.now(UTC) - timedelta(hours=_TIMEOUT_HOURS + 1)
        async with factory() as db:
            project_id = await _add_project(
                db,
                phase=PHASE_BRIEF,
                phase_status=PHASE_STATUS_AWAITING_HUMAN,
                updated_at=stale,
            )

            rejected = await _service().auto_reject_stuck(db, _TIMEOUT_HOURS)
            await db.commit()

            assert rejected == 1
            project = await db.get(CarouselProjectModel, project_id)
            assert project is not None
            assert project.phase_status == PHASE_STATUS_REJECTED

    async def test_published_workflow_is_not_rejected(self, test_engine) -> None:
        factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        stale = datetime.now(UTC) - timedelta(hours=_TIMEOUT_HOURS + 1)
        async with factory() as db:
            project_id = await _add_project(
                db,
                phase=PHASE_PUBLISHED,
                phase_status=PHASE_STATUS_PENDING,
                updated_at=stale,
            )

            rejected = await _service().auto_reject_stuck(db, _TIMEOUT_HOURS)
            await db.commit()

            assert rejected == 0
            project = await db.get(CarouselProjectModel, project_id)
            assert project is not None
            assert project.phase_status == PHASE_STATUS_PENDING
