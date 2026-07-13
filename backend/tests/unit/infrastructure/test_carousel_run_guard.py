"""Unit tests for the AE-0315 run-column invariant + run-epoch flush fence.

Feature: tests/features/carousel_run_progress_reaper.feature
Covers: atomic stamp/clear on phase_status value changes (incl. the three
write-owner bypass sites), no-op-hydrate safety, and the layer-(a) flush
fence semantics (contextvar-gated; user writes never falsely rejected).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.application.services.phase5_migration_service import (
    Phase5MigrationReport,
    Phase5MigrationService,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_BRIEF,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_PENDING,
    PHASE_STATUS_REJECTED,
)
from rag_backend.domain.models.carousel_run import (
    CarouselRunContext,
    StaleRunEpochError,
    carousel_run_epoch_var,
)
from rag_backend.infrastructure.database.models.carousel import (
    CarouselProjectModel,
    CarouselSlideModel,
)
from rag_backend.infrastructure.database.workflow_timeout_repository import (
    WorkflowTimeoutRepository,
)
from rag_backend.infrastructure.events.memory_event_publisher import (
    MemoryEventPublisher,
)

_NON_IN_PROGRESS_STATUSES = [
    PHASE_STATUS_PENDING,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_REJECTED,
    PHASE_STATUS_FAILED,
]


def _project(phase_status: str) -> CarouselProjectModel:
    return CarouselProjectModel(
        id=str(uuid.uuid4()),
        topic="Run guard",
        audience="Devs",
        niche="Tech",
        status="pending",
        current_phase=PHASE_BRIEF,
        phase_status=phase_status,
    )


def _factory(test_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def _add_in_progress_with_run_columns(db: AsyncSession) -> str:
    """Insert a row then transition it into in_progress (stamping run cols)."""
    project = _project(PHASE_STATUS_AWAITING_HUMAN)
    db.add(project)
    await db.commit()
    project.phase_status = PHASE_STATUS_IN_PROGRESS
    await db.commit()
    assert project.run_started_at is not None
    assert project.run_heartbeat_at is not None
    return str(project.id)


@pytest.fixture
def run_context():
    """Setter for the run-ownership contextvar (test-coroutine scoped).

    pytest-asyncio runs each test coroutine in its own Context, so a value
    set inside the test body dies with the test; the teardown clears the
    fixture's own context defensively.
    """

    def _set(project_id: str, epoch: int) -> None:
        carousel_run_epoch_var.set(
            CarouselRunContext(project_id=project_id, epoch=epoch)
        )

    yield _set
    carousel_run_epoch_var.set(None)


@pytest.mark.asyncio
class TestRunColumnInvariant:
    """Scenario: banner columns stamped/cleared atomically with phase_status."""

    async def test_transition_into_in_progress_stamps_run_columns(
        self, test_engine
    ) -> None:
        async with _factory(test_engine)() as db:
            await _add_in_progress_with_run_columns(db)

    @pytest.mark.parametrize("target_status", _NON_IN_PROGRESS_STATUSES)
    async def test_every_non_in_progress_transition_clears_run_columns(
        self, test_engine, target_status: str
    ) -> None:
        # Suite-wide assertion (ticket AC): EVERY value-changing transition to
        # a non-in_progress status clears the run columns in the same flush.
        async with _factory(test_engine)() as db:
            project_id = await _add_in_progress_with_run_columns(db)
            project = await db.get(CarouselProjectModel, project_id)
            assert project is not None
            project.phase_status = target_status
            await db.commit()
            assert project.run_started_at is None
            assert project.run_heartbeat_at is None

    async def test_noop_hydrate_never_clears_live_run_columns(
        self, test_engine
    ) -> None:
        # Owner-bypass site #3: update_from_entity re-writing the SAME
        # phase_status (no-op hydrate) must not clear a live run's columns.
        async with _factory(test_engine)() as db:
            project_id = await _add_in_progress_with_run_columns(db)
            project = await db.get(CarouselProjectModel, project_id)
            assert project is not None
            entity = project.to_entity()
            entity.title = "Hydrated title"  # unrelated column change
            project.update_from_entity(entity)
            assert project.phase_status == PHASE_STATUS_IN_PROGRESS
            await db.commit()
            assert project.run_started_at is not None
            assert project.run_heartbeat_at is not None

    async def test_hydrator_transition_out_clears_run_columns(
        self, test_engine
    ) -> None:
        # Owner-bypass site #3 (value-changing case): the hydrator flipping
        # phase_status out of in_progress clears the run columns.
        async with _factory(test_engine)() as db:
            project_id = await _add_in_progress_with_run_columns(db)
            project = await db.get(CarouselProjectModel, project_id)
            assert project is not None
            entity = project.to_entity()
            entity.phase_status = PHASE_STATUS_APPROVED
            project.update_from_entity(entity)
            await db.commit()
            assert project.run_started_at is None
            assert project.run_heartbeat_at is None

    async def test_timeout_auto_reject_clears_leftover_run_columns(
        self, test_engine
    ) -> None:
        # Owner-bypass site #1: workflow_timeout_repository._reject flips
        # phase_status directly; leftover run columns must clear with it.
        async with _factory(test_engine)() as db:
            project = _project(PHASE_STATUS_AWAITING_HUMAN)
            project.run_started_at = datetime.now(UTC)
            project.updated_at = datetime(2020, 1, 1, tzinfo=UTC)
            db.add(project)
            await db.commit()
            repo = WorkflowTimeoutRepository(
                WorkflowEventService(MemoryEventPublisher())
            )
            rejected = await repo.auto_reject_stuck(db, 1)
            await db.commit()
            assert rejected == 1
            assert project.phase_status == PHASE_STATUS_REJECTED
            assert project.run_started_at is None

    async def test_phase5_backfill_clears_run_columns(self, test_engine) -> None:
        # Owner-bypass site #2: the phase-5 migration backfill writes
        # phase_status without the write owner.
        async with _factory(test_engine)() as db:
            project = _project(PHASE_STATUS_IN_PROGRESS)
            project.current_phase = PHASE_BRIEF
            project.run_started_at = datetime.now(UTC)
            project.run_heartbeat_at = datetime.now(UTC)
            project.status = "completed"
            db.add(project)
            await db.commit()
            report = Phase5MigrationReport()
            Phase5MigrationService._backfill_workflow_state(project, report)
            assert project.phase_status != PHASE_STATUS_IN_PROGRESS
            await db.commit()
            assert project.run_started_at is None
            assert project.run_heartbeat_at is None


@pytest.mark.asyncio
class TestRunEpochFlushFence:
    """Scenario: fencing safety — zombie rejected, user writes never blocked."""

    async def test_non_run_write_concurrent_with_epoch_bump_succeeds(
        self, test_engine
    ) -> None:
        # Contextvar unset (user/admin/operator context): a write racing a
        # reaper epoch bump must NEVER be rejected by the fence.
        factory = _factory(test_engine)
        async with factory() as db:
            project_id = await _add_in_progress_with_run_columns(db)
        async with factory() as other:
            await other.execute(
                update(CarouselProjectModel)
                .where(CarouselProjectModel.id == project_id)
                .values(run_epoch=CarouselProjectModel.run_epoch + 1)
            )
            await other.commit()
        async with factory() as db:
            project = await db.get(CarouselProjectModel, project_id)
            assert project is not None
            project.title = "user edit after reap"
            await db.commit()
            assert project.title == "user edit after reap"

    async def test_run_owned_write_with_stale_epoch_is_rejected(
        self, test_engine, run_context
    ) -> None:
        factory = _factory(test_engine)
        async with factory() as db:
            project_id = await _add_in_progress_with_run_columns(db)
        async with factory() as other:
            await other.execute(
                update(CarouselProjectModel)
                .where(CarouselProjectModel.id == project_id)
                .values(run_epoch=CarouselProjectModel.run_epoch + 1)
            )
            await other.commit()
        run_context(project_id, 0)  # captured before the bump -> stale
        async with factory() as db:
            project = await db.get(CarouselProjectModel, project_id)
            assert project is not None
            project.title = "zombie write"
            with pytest.raises(StaleRunEpochError):
                await db.flush()

    async def test_run_owned_write_with_current_epoch_passes(
        self, test_engine, run_context
    ) -> None:
        factory = _factory(test_engine)
        async with factory() as db:
            project_id = await _add_in_progress_with_run_columns(db)
        run_context(project_id, 0)  # row epoch is still 0 -> current
        async with factory() as db:
            project = await db.get(CarouselProjectModel, project_id)
            assert project is not None
            project.title = "healthy run write"
            await db.commit()
            assert project.title == "healthy run write"

    async def test_slide_write_is_fenced_at_the_same_boundary(
        self, test_engine, run_context
    ) -> None:
        # Concurrent per-slide writes share the run context; a stale-epoch
        # slide INSERT is rejected at the same flush boundary.
        factory = _factory(test_engine)
        async with factory() as db:
            project_id = await _add_in_progress_with_run_columns(db)
        async with factory() as other:
            await other.execute(
                update(CarouselProjectModel)
                .where(CarouselProjectModel.id == project_id)
                .values(run_epoch=CarouselProjectModel.run_epoch + 1)
            )
            await other.commit()
        run_context(project_id, 0)
        async with factory() as db:
            db.add(
                CarouselSlideModel(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    slide_number=1,
                    slide_type="intro",
                    heading="h",
                    body="b",
                )
            )
            with pytest.raises(StaleRunEpochError):
                await db.flush()

    async def test_fence_ignores_other_projects(self, test_engine, run_context) -> None:
        factory = _factory(test_engine)
        async with factory() as db:
            fenced_id = await _add_in_progress_with_run_columns(db)
            other_project = _project(PHASE_STATUS_AWAITING_HUMAN)
            db.add(other_project)
            await db.commit()
            run_context(fenced_id, 99)  # stale for fenced_id
            other_project.title = "unrelated project write"
            await db.commit()
            assert other_project.title == "unrelated project write"

    async def test_columns_exist_with_epoch_default_zero(self, test_engine) -> None:
        # Migration parity: create_all gives SQLite the three columns; the
        # epoch server-default is 0.
        async with _factory(test_engine)() as db:
            project = _project(PHASE_STATUS_PENDING)
            db.add(project)
            await db.commit()
            row = (
                await db.execute(
                    select(
                        CarouselProjectModel.run_started_at,
                        CarouselProjectModel.run_heartbeat_at,
                        CarouselProjectModel.run_epoch,
                    ).where(CarouselProjectModel.id == str(project.id))
                )
            ).one()
            assert row.run_started_at is None
            assert row.run_heartbeat_at is None
            assert row.run_epoch == 0
