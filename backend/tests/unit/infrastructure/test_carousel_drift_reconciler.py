"""Unit tests for the autonomous carousel drift reconciler (AE-0311).

Gherkin: tests/features/carousel_deterministic_repair.feature
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from structlog.testing import capture_logs

from rag_backend.domain.constants.carousel_repair import (
    LOG_EVENT_DRIFT_CONVERGED,
    LOG_EVENT_DRIFT_DETECTED,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.models.carousel_run import carousel_run_epoch_var
from rag_backend.infrastructure.database.carousel_drift_reconciler import (
    CarouselDriftReconcilerRepository,
)
from rag_backend.infrastructure.database.models.carousel import (
    CarouselProjectModel,
    CarouselSlideModel,
)

_V1 = "hero_lower_third_v1"
_CLEAN_BODY = "Um corpo limpo, curto e valido para o slide."
_SCAFFOLD_BODY = (
    "## PT\n**Heading:** x\n**Body:** " + ("palavra " * 80) + "\n## EN\n**Body:** y."
)


def _factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class _FakeGateway:
    """Checkpoint gateway double capturing writes + the stamped epoch."""

    def __init__(self, state: dict[str, object] | None) -> None:
        self.state = state
        self.writes: list[dict[str, object]] = []
        self.write_epoch: int | None = None

    async def read_state(self, project_id: str) -> dict[str, object] | None:
        return self.state

    async def write_state(self, project_id: str, values: dict[str, object]) -> None:
        context = carousel_run_epoch_var.get()
        self.write_epoch = context.epoch if context is not None else None
        self.writes.append(values)


async def _reset(db: AsyncSession) -> None:
    """Session-scoped engine shares rows across tests; isolate each case."""
    await db.execute(delete(CarouselSlideModel))
    await db.execute(delete(CarouselProjectModel))
    await db.commit()


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_rows(test_engine: AsyncEngine) -> AsyncIterator[None]:
    """Purge committed rows so other test files see a clean database."""
    yield
    async with _factory(test_engine)() as db:
        await _reset(db)


async def _add(
    db: AsyncSession,
    *,
    body: str,
    phase_status: str = PHASE_STATUS_AWAITING_HUMAN,
    status: str = "in_review",
    run_epoch: int = 2,
) -> str:
    project = CarouselProjectModel(
        id=str(uuid.uuid4()),
        topic="Drift",
        audience="Devs",
        niche="Tech",
        status=status,
        current_phase="design",
        phase_status=phase_status,
        lock_version=1,
        presentation_policy_version=_V1,
    )
    project.run_epoch = run_epoch
    db.add(project)
    await db.flush()
    db.add(
        CarouselSlideModel(
            id=str(uuid.uuid4()),
            project_id=project.id,
            slide_number=4,
            slide_type="content",
            heading="Um titulo valido",
            body=body,
            extras={"translation_en": {"heading": "A title", "body": "A body."}},
        )
    )
    await db.commit()
    return str(project.id)


def _blocking_state() -> dict[str, object]:
    return {
        "presentation_validation": {
            "validation_status": "invalid",
            "validated_at": "2026-07-10T00:00:00Z",
            "blocking": True,
            "violations": [{"code": "drafting_scaffold_present", "message": "x"}],
        }
    }


@pytest.mark.asyncio
class TestDriftReconciler:
    async def test_converges_repaired_projection_with_stale_checkpoint(
        self, test_engine: AsyncEngine
    ) -> None:
        # Scenario: partial failure left a clean projection + stale-blocking
        # checkpoint; the watchdog converges it with no client retry.
        async with _factory(test_engine)() as db:
            await _reset(db)
            await _add(db, body=_CLEAN_BODY, run_epoch=5)
            gateway = _FakeGateway(_blocking_state())
            reconciler = CarouselDriftReconcilerRepository(gateway)
            with capture_logs() as logs:
                converged = await reconciler.reconcile(db)
            assert converged == 1
            assert gateway.writes
            written = gateway.writes[0]["presentation_validation"]
            assert isinstance(written, dict) and written["blocking"] is False
            assert gateway.write_epoch == 5  # stamped the row's CURRENT epoch
            events = {log["event"] for log in logs}
            assert LOG_EVENT_DRIFT_DETECTED in events
            assert LOG_EVENT_DRIFT_CONVERGED in events

    async def test_genuine_blocking_projection_is_not_converged(
        self, test_engine: AsyncEngine
    ) -> None:
        async with _factory(test_engine)() as db:
            await _reset(db)
            await _add(db, body=_SCAFFOLD_BODY)
            gateway = _FakeGateway(_blocking_state())
            converged = await CarouselDriftReconcilerRepository(gateway).reconcile(db)
            assert converged == 0
            assert gateway.writes == []

    async def test_non_blocking_checkpoint_is_skipped(
        self, test_engine: AsyncEngine
    ) -> None:
        async with _factory(test_engine)() as db:
            await _reset(db)
            await _add(db, body=_CLEAN_BODY)
            gateway = _FakeGateway({"presentation_validation": {"blocking": False}})
            converged = await CarouselDriftReconcilerRepository(gateway).reconcile(db)
            assert converged == 0
            assert gateway.writes == []

    async def test_in_progress_rows_are_ignored(self, test_engine: AsyncEngine) -> None:
        async with _factory(test_engine)() as db:
            await _reset(db)
            await _add(db, body=_CLEAN_BODY, phase_status=PHASE_STATUS_IN_PROGRESS)
            gateway = _FakeGateway(_blocking_state())
            converged = await CarouselDriftReconcilerRepository(gateway).reconcile(db)
            assert converged == 0


@pytest.mark.asyncio
class TestPhaseDriftReconciliation:
    """AE-0320 scenarios (tests/features/carousel_run_lock_safety.feature)."""

    async def _row(self, db: AsyncSession, project_id: str) -> CarouselProjectModel:
        found = await db.get(CarouselProjectModel, project_id)
        assert found is not None
        return found

    async def test_failed_row_converges_to_parked_checkpoint_phase(
        self, test_engine: AsyncEngine
    ) -> None:
        """Scenario: Failed row behind an advanced parked checkpoint converges."""
        async with _factory(test_engine)() as db:
            await _reset(db)
            project_id = await _add(
                db, body=_CLEAN_BODY, phase_status=PHASE_STATUS_FAILED
            )
            gateway = _FakeGateway({
                "current_phase": "images",
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            })
            reconciler = CarouselDriftReconcilerRepository(gateway)

            with capture_logs() as logs:
                converged = await reconciler.reconcile(db)
            await db.commit()

            assert converged == 1
            row = await self._row(db, project_id)
            assert row.current_phase == "images"
            assert row.phase_status == PHASE_STATUS_AWAITING_HUMAN
            assert int(row.lock_version) == 2
            assert int(row.run_epoch) == 3
            assert row.run_started_at is None
            assert row.run_heartbeat_at is None
            events = [
                log for log in logs if log["event"] == "carousel_phase_drift_converged"
            ]
            assert len(events) == 1
            assert events[0]["from_phase"] == "design"
            assert events[0]["to_phase"] == "images"

    async def test_same_phase_failure_stays_failed(
        self, test_engine: AsyncEngine
    ) -> None:
        """Scenario: Same-phase failure is left for the recovery UI."""
        async with _factory(test_engine)() as db:
            await _reset(db)
            project_id = await _add(
                db, body=_CLEAN_BODY, phase_status=PHASE_STATUS_FAILED
            )
            gateway = _FakeGateway({
                "current_phase": "design",
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            })
            reconciler = CarouselDriftReconcilerRepository(gateway)

            assert await reconciler.reconcile(db) == 0
            row = await self._row(db, project_id)
            assert row.phase_status == PHASE_STATUS_FAILED

    async def test_mid_step_checkpoint_not_converged(
        self, test_engine: AsyncEngine
    ) -> None:
        """Scenario: Mid-step checkpoint never triggers phase convergence."""
        async with _factory(test_engine)() as db:
            await _reset(db)
            project_id = await _add(
                db, body=_CLEAN_BODY, phase_status=PHASE_STATUS_FAILED
            )
            gateway = _FakeGateway({
                "current_phase": "images",
                "phase_status": PHASE_STATUS_IN_PROGRESS,
            })
            reconciler = CarouselDriftReconcilerRepository(gateway)

            assert await reconciler.reconcile(db) == 0
            row = await self._row(db, project_id)
            assert row.phase_status == PHASE_STATUS_FAILED

    async def test_completed_projects_are_ignored(
        self, test_engine: AsyncEngine
    ) -> None:
        async with _factory(test_engine)() as db:
            await _reset(db)
            project_id = await _add(
                db,
                body=_CLEAN_BODY,
                phase_status=PHASE_STATUS_FAILED,
                status="completed",
            )
            gateway = _FakeGateway({
                "current_phase": "images",
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            })
            reconciler = CarouselDriftReconcilerRepository(gateway)

            assert await reconciler.reconcile(db) == 0
            row = await self._row(db, project_id)
            assert row.phase_status == PHASE_STATUS_FAILED
