"""The carousel reject bumps ``lock_version`` once.

Feature: tests/features/reject_bumps_lock_version_ae0604.feature

Every test uses the ``no_outbox_relay`` fixture: commits here would otherwise run
the outbox relay on a foreign engine.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.application.services.optimistic_lock_service import (
    CarouselVersionBumpParams,
    OptimisticLockService,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_REJECTED,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.constants.workflow_timeout import (
    ESCALATION_EXPIRED_EVENT_SOURCE,
    ESCALATION_EXPIRED_REJECT_MESSAGE,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.workflow_timeout_repository import (
    RejectCause,
    WorkflowTimeoutRepository,
)
from rag_backend.infrastructure.events.memory_event_publisher import (
    MemoryEventPublisher,
)

pytestmark = pytest.mark.usefixtures("no_outbox_relay")

_TIMEOUT_HOURS = 72
_VERSION = 5


def _repository() -> WorkflowTimeoutRepository:
    return WorkflowTimeoutRepository(WorkflowEventService(MemoryEventPublisher()))


def _sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _add(db: AsyncSession, idle_hours: int) -> str:
    """A carousel waiting for a human at research, idle ``idle_hours``."""
    project_id = str(uuid.uuid4())
    updated_at = datetime.now(UTC) - timedelta(hours=idle_hours)
    db.add(
        CarouselProjectModel(
            id=project_id,
            topic="Stale review",
            audience="Devs",
            niche="Tech",
            status="draft",
            current_phase=PHASE_RESEARCH,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            lock_version=_VERSION,
            updated_at=updated_at,
            created_at=updated_at,
        )
    )
    await db.commit()
    return project_id


async def _version(engine: AsyncEngine, project_id: str) -> tuple[str | None, int]:
    async with _sessions(engine)() as db:
        project = await db.get(CarouselProjectModel, project_id)
        assert project is not None
        return project.phase_status, int(project.lock_version)


async def _drop(engine: AsyncEngine, project_id: str) -> None:
    """Delete a still-waiting row: the session-scoped engine is shared."""
    async with _sessions(engine)() as db:
        project = await db.get(CarouselProjectModel, project_id)
        assert project is not None
        await db.delete(project)
        await db.commit()


@pytest.mark.asyncio
class TestRejectBumpsLockVersion:
    # Scenario: The reject bumps the lock version once
    async def test_reject_with_any_cause_bumps_once(
        self, test_engine: AsyncEngine
    ) -> None:
        cause = RejectCause(
            reason=ESCALATION_EXPIRED_REJECT_MESSAGE,
            source=ESCALATION_EXPIRED_EVENT_SOURCE,
            timeout_hours=_TIMEOUT_HOURS,
        )
        async with _sessions(test_engine)() as db:
            project_id = await _add(db, idle_hours=1)
            project = await db.get(CarouselProjectModel, project_id)
            assert project is not None

            await _repository().reject(db, project, cause)
            await db.commit()

        assert await _version(test_engine, project_id) == (
            PHASE_STATUS_REJECTED,
            _VERSION + 1,
        )

    # Scenario: The reject bumps the lock version once
    async def test_sweep_bumps_the_rejected_and_keeps_the_rest(
        self, test_engine: AsyncEngine
    ) -> None:
        async with _sessions(test_engine)() as db:
            stuck = await _add(db, idle_hours=_TIMEOUT_HOURS + 1)
            recent = await _add(db, idle_hours=_TIMEOUT_HOURS - 1)

            rejected = await _repository().auto_reject_stuck(db, _TIMEOUT_HOURS)
            await db.commit()

        assert rejected == 1
        assert await _version(test_engine, stuck) == (
            PHASE_STATUS_REJECTED,
            _VERSION + 1,
        )
        assert await _version(test_engine, recent) == (
            PHASE_STATUS_AWAITING_HUMAN,
            _VERSION,
        )
        await _drop(test_engine, recent)

    # Scenario: A stale owner approve after a stuck-sweep reject is refused
    async def test_a_cas_at_the_pre_reject_version_conflicts(
        self, test_engine: AsyncEngine
    ) -> None:
        async with _sessions(test_engine)() as db:
            project_id = await _add(db, idle_hours=_TIMEOUT_HOURS + 1)
            assert await _repository().auto_reject_stuck(db, _TIMEOUT_HOURS) == 1
            await db.commit()

        async with _sessions(test_engine)() as db:
            with pytest.raises(ValueError, match=ERR_VERSION_CONFLICT):
                await OptimisticLockService().bump_carousel_version(
                    db,
                    CarouselVersionBumpParams(
                        project_id=project_id, expected_version=_VERSION
                    ),
                )
            await db.rollback()

        assert await _version(test_engine, project_id) == (
            PHASE_STATUS_REJECTED,
            _VERSION + 1,
        )
