"""Unit tests for the AE-0315 stale-run reaper.

Feature: tests/features/carousel_run_progress_reaper.feature
Scenarios: dead run reaped + recovery, slow-healthy never reaped, overdue
alert, NULL-heartbeat migration-day safety, N-consecutive observations,
reap-vs-repair CAS serialization, zombie-rejected/replacement-accepted.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.application.services.optimistic_lock_service import (
    CarouselVersionBumpParams,
    OptimisticLockService,
)
from rag_backend.domain.constants.carousel_run import (
    RUN_FINISHED_REASON_STALE,
    SSE_EVENT_RUN_FINISHED,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.models.carousel_run import (
    CarouselRunContext,
    StaleRunEpochError,
    carousel_run_epoch_var,
)
from rag_backend.infrastructure.database.carousel_run_reaper import (
    CarouselRunReaperConfig,
    CarouselRunReaperRepository,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

_STALE_SECONDS = 180
_OBSERVATIONS = 3
_OVERDUE_MINUTES = 60

_HUB_PATH = (
    "rag_backend.application.services.carousel.workflow_sse_hub.get_workflow_sse_hub"
)


def _config() -> CarouselRunReaperConfig:
    return CarouselRunReaperConfig(
        heartbeat_stale_seconds=_STALE_SECONDS,
        reap_observations=_OBSERVATIONS,
        overdue_minutes=_OVERDUE_MINUTES,
    )


def _reaper(
    checkpoint_status: str | None = None,
) -> CarouselRunReaperRepository:
    async def _reader(_project_id: str) -> str | None:
        return checkpoint_status

    return CarouselRunReaperRepository(
        _config(),
        checkpoint_reader=_reader if checkpoint_status is not None else None,
    )


def _factory(test_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def _add_run_row(
    db: AsyncSession,
    *,
    heartbeat_age_seconds: int | None,
    started_minutes_ago: int = 5,
    phase_status: str = PHASE_STATUS_IN_PROGRESS,
) -> CarouselProjectModel:
    now = datetime.now(UTC)
    project = CarouselProjectModel(
        id=str(uuid.uuid4()),
        topic="Reaper",
        audience="Devs",
        niche="Tech",
        status="pending",
        current_phase=PHASE_CONTENT,
        phase_status=phase_status,
        lock_version=3,
    )
    db.add(project)
    await db.commit()
    # Stamp run columns directly (simulating a run that started pre-restart;
    # the listener path is covered by test_carousel_run_guard).
    project.run_started_at = now - timedelta(minutes=started_minutes_ago)
    if heartbeat_age_seconds is not None:
        project.run_heartbeat_at = now - timedelta(seconds=heartbeat_age_seconds)
    await db.commit()
    return project


async def _tick_times(
    reaper: CarouselRunReaperRepository,
    db: AsyncSession,
    times: int,
) -> int:
    total = 0
    for _ in range(times):
        total += await reaper.tick(db)
        await db.commit()
    return total


@pytest.mark.asyncio
class TestReaperRules:
    # Scenario: Dead run is reaped and the user recovers without an operator
    async def test_dead_run_reaped_after_n_stale_observations(
        self, test_engine
    ) -> None:
        hub = AsyncMock()
        async with _factory(test_engine)() as db:
            project = await _add_run_row(db, heartbeat_age_seconds=_STALE_SECONDS + 60)
            reaper = _reaper()
            with patch(_HUB_PATH, return_value=hub):
                assert await _tick_times(reaper, db, 2) == 0
                assert project.phase_status == PHASE_STATUS_IN_PROGRESS
                assert await _tick_times(reaper, db, 1) == 1
            await db.refresh(project)
            assert project.phase_status == PHASE_STATUS_AWAITING_HUMAN
            assert project.run_started_at is None
            assert project.run_heartbeat_at is None
            assert project.lock_version == 4  # bumped in the same UPDATE
            assert project.run_epoch == 1  # fencing token bumped
            event = hub.publish.await_args.args[1]
            assert event["event"] == SSE_EVENT_RUN_FINISHED
            assert event["reason"] == RUN_FINISHED_REASON_STALE

    async def test_reap_reconciles_parked_checkpoint_by_mirroring(
        self, test_engine
    ) -> None:
        # Checkpoint parked (approved) -> the row mirrors it, not awaiting_human.
        async with _factory(test_engine)() as db:
            project = await _add_run_row(db, heartbeat_age_seconds=_STALE_SECONDS + 60)
            reaper = _reaper(checkpoint_status=PHASE_STATUS_APPROVED)
            with patch(_HUB_PATH, return_value=AsyncMock()):
                await _tick_times(reaper, db, _OBSERVATIONS)
            await db.refresh(project)
            assert project.phase_status == PHASE_STATUS_APPROVED

    async def test_mid_step_checkpoint_resets_to_awaiting_human(
        self, test_engine
    ) -> None:
        # Mid-generation-shaped checkpoint (in_progress): the reaper NEVER
        # touches checkpoint state — the row resets to awaiting_human so
        # LangGraph re-executes the interrupted node on the next resume
        # (pre-interrupt side effects are idempotent by project rule).
        async with _factory(test_engine)() as db:
            project = await _add_run_row(db, heartbeat_age_seconds=_STALE_SECONDS + 60)
            reaper = _reaper(checkpoint_status=PHASE_STATUS_IN_PROGRESS)
            with patch(_HUB_PATH, return_value=AsyncMock()):
                await _tick_times(reaper, db, _OBSERVATIONS)
            await db.refresh(project)
            assert project.phase_status == PHASE_STATUS_AWAITING_HUMAN

    # Scenario: Slow healthy run is alerted but never reaped
    async def test_slow_healthy_run_never_reaped(self, test_engine) -> None:
        async with _factory(test_engine)() as db:
            project = await _add_run_row(
                db, heartbeat_age_seconds=10, started_minutes_ago=70
            )
            reaper = _reaper()
            with patch(
                "rag_backend.infrastructure.database.carousel_run_reaper.logger"
            ) as log:
                assert await _tick_times(reaper, db, _OBSERVATIONS + 2) == 0
            await db.refresh(project)
            assert project.phase_status == PHASE_STATUS_IN_PROGRESS
            assert project.run_epoch == 0
            # Scenario: Overdue run is flagged for operators
            overdue_calls = [
                call
                for call in log.warning.call_args_list
                if call.args and call.args[0] == "run_overdue"
            ]
            assert overdue_calls
            assert overdue_calls[0].kwargs["project_id"] == str(project.id)
            assert overdue_calls[0].kwargs["elapsed_minutes"] >= 60

    async def test_null_heartbeat_is_alert_only_forever(self, test_engine) -> None:
        # Migration-day safety: an in_progress row predating the columns has
        # NULL heartbeat forever from the reaper's view — never reapable.
        async with _factory(test_engine)() as db:
            project = await _add_run_row(
                db, heartbeat_age_seconds=None, started_minutes_ago=300
            )
            project.run_started_at = None  # fully pre-migration shape
            await db.commit()
            reaper = _reaper()
            assert await _tick_times(reaper, db, _OBSERVATIONS * 3) == 0
            await db.refresh(project)
            assert project.phase_status == PHASE_STATUS_IN_PROGRESS

    async def test_non_in_progress_rows_never_reaped(self, test_engine) -> None:
        # Leftover run_started_at on a non-in_progress row is ignored.
        async with _factory(test_engine)() as db:
            project = await _add_run_row(
                db,
                heartbeat_age_seconds=_STALE_SECONDS * 10,
                phase_status=PHASE_STATUS_AWAITING_HUMAN,
            )
            reaper = _reaper()
            assert await _tick_times(reaper, db, _OBSERVATIONS + 1) == 0
            await db.refresh(project)
            assert project.phase_status == PHASE_STATUS_AWAITING_HUMAN

    async def test_fresh_heartbeat_resets_consecutive_count(self, test_engine) -> None:
        # Heartbeat robustness: a recovered heartbeat resets the count, so a
        # transient blip never accumulates into a reap.
        async with _factory(test_engine)() as db:
            project = await _add_run_row(db, heartbeat_age_seconds=_STALE_SECONDS + 60)
            reaper = _reaper()
            assert await _tick_times(reaper, db, _OBSERVATIONS - 1) == 0
            project.run_heartbeat_at = datetime.now(UTC)  # heartbeat recovers
            await db.commit()
            assert await _tick_times(reaper, db, 1) == 0
            project.run_heartbeat_at = datetime.now(UTC) - timedelta(
                seconds=_STALE_SECONDS + 60
            )
            await db.commit()
            # Needs N fresh consecutive observations again.
            assert await _tick_times(reaper, db, _OBSERVATIONS - 1) == 0
            with patch(_HUB_PATH, return_value=AsyncMock()):
                assert await _tick_times(reaper, db, 1) == 1


@pytest.mark.asyncio
class TestReapSerialization:
    async def test_post_reap_resume_cas_with_old_version_fails(
        self, test_engine
    ) -> None:
        # Reap-vs-repair serialization: an in-flight resume holding the
        # pre-reap lock_version fails its CAS after the reap bump.
        async with _factory(test_engine)() as db:
            project = await _add_run_row(db, heartbeat_age_seconds=_STALE_SECONDS + 60)
            old_version = int(project.lock_version)
            reaper = _reaper()
            with patch(_HUB_PATH, return_value=AsyncMock()):
                await _tick_times(reaper, db, _OBSERVATIONS)
            with pytest.raises(ValueError, match=ERR_VERSION_CONFLICT):
                await OptimisticLockService().bump_carousel_version(
                    db,
                    CarouselVersionBumpParams(
                        project_id=str(project.id),
                        expected_version=old_version,
                    ),
                )

    async def test_zombie_rejected_and_replacement_accepted_same_project(
        self, test_engine
    ) -> None:
        # Fencing safety (the boolean-marker impossibility case): after a
        # reap, the zombie's stale-epoch write fails while the replacement
        # run's current-epoch write succeeds — no clearing step exists.
        factory = _factory(test_engine)
        async with factory() as db:
            project = await _add_run_row(db, heartbeat_age_seconds=_STALE_SECONDS + 60)
            project_id = str(project.id)
            reaper = _reaper()
            with patch(_HUB_PATH, return_value=AsyncMock()):
                await _tick_times(reaper, db, _OBSERVATIONS)
        async with factory() as db:
            carousel_run_epoch_var.set(
                CarouselRunContext(project_id=project_id, epoch=0)  # zombie
            )
            zombie = await db.get(CarouselProjectModel, project_id)
            assert zombie is not None
            zombie.title = "zombie write"
            with pytest.raises(StaleRunEpochError):
                await db.flush()
            await db.rollback()
            carousel_run_epoch_var.set(
                CarouselRunContext(project_id=project_id, epoch=1)  # replacement
            )
            replacement = await db.get(CarouselProjectModel, project_id)
            assert replacement is not None
            replacement.title = "replacement write"
            await db.commit()
            assert replacement.title == "replacement write"
            carousel_run_epoch_var.set(None)
