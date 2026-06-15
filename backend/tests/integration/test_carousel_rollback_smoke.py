"""Trace-correlated rollback smoke comparison (AE-0113 / ADR-0009 §2, §7).

Runnable, deterministic portion of the scaled-down carousel rollback drill.
The live ``pg_restore`` step is operator-run (no live Postgres in CI; see
``docs/architecture/carousel-rollback-drill.md``). Here we exercise the
automatable invariant against in-memory SQLite, matching the rest of
``tests/integration``:

  * a database restore returns the carousel workflow state AND its
    trace-correlated audit-event sequence to a state byte-identical to the
    pre-change baseline (``compare_snapshots`` matches), and
  * the smoke comparison actually has teeth — it DETECTS divergence when the
    restore is incomplete (negative case).

External clients (LLM, image gen, Pinecone) are never invoked; no API keys
are required.

Gherkin:

  Feature: Carousel rollback restores a byte-identical workflow trace
    Scenario: restore matches the pre-change baseline
      Given a captured baseline snapshot of carousel workflow state + trace
      When a forward change is applied and then a restore reverts it
      Then a trace-correlated smoke comparison reports an exact match
    Scenario: incomplete restore is detected
      Given a captured baseline snapshot
      When a restore leaves residual drift
      Then the smoke comparison reports the difference
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.domain.models import CarouselProject, CarouselTheme
from rag_backend.infrastructure.database.config import Base, close_db
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)

DRILL_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "carousel_rollback_drill.py"
)

EVENT_TYPE_STARTED = "workflow.phase.started"
EVENT_TYPE_APPROVED = "workflow.phase.approved"
EVENT_TYPE_DRIFT = "workflow.phase.unexpected"
WORKFLOW_STATUS_BASELINE = "in_review"
PHASE_STATUS_BASELINE = "awaiting_human"


def _load_drill() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "carousel_rollback_drill", DRILL_SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
async def session() -> AsyncSession:
    """In-memory SQLite session for the rollback drill smoke test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    maker = db_config.get_session_maker()
    async with maker() as db:
        yield db
    db_config.c_engine = None
    await close_db()
    await engine.dispose()


async def _seed_baseline(db: AsyncSession) -> str:
    """Persist a carousel project + two trace-correlated audit events."""
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )

    repo = PostgresCarouselRepository(db)
    project = CarouselProject(
        topic="Rollback Drill Project",
        audience="Devs",
        niche="AI",
        theme=CarouselTheme.AUTO,
        owner_id=str(uuid4()),
        output_dir="/tmp/rollback-drill-output",
    )
    created = await repo.create_project(project)
    project_id = str(created.id)

    model = await db.get(CarouselProjectModel, project_id)
    assert model is not None
    model.workflow_status = WORKFLOW_STATUS_BASELINE
    model.phase_status = PHASE_STATUS_BASELINE
    model.phase_progress = {"research": "done", "outline": "awaiting_human"}
    model.lock_version = 3

    for version, event_type in enumerate(
        (EVENT_TYPE_STARTED, EVENT_TYPE_APPROVED), start=1
    ):
        db.add(
            WorkflowAuditLogModel(
                event_id=str(uuid4()),
                event_type=event_type,
                aggregate_id=project_id,
                aggregate_type="project",
                version=version,
                payload={"phase": "research", "version": version},
                metadata_json={"project_id": project_id},
            )
        )
    await db.commit()
    return project_id


class TestCarouselRollbackSmokeComparison:
    """Scenario suite for the scaled-down rollback drill smoke comparison."""

    @pytest.mark.asyncio
    async def test_restore_matches_baseline_trace(self, session: AsyncSession) -> None:
        """Restore reverts state + trace to a byte-identical baseline."""
        drill = _load_drill()
        project_id = await _seed_baseline(session)

        baseline = await drill.snapshot_carousel_state(session, project_id)
        assert baseline is not None
        assert len(baseline.audit_trace) == 2

        # --- forward change: mutate the row and append a drift audit event ---
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        model.workflow_status = "approved_for_publish"
        model.phase_status = "in_progress"
        model.lock_version = 4
        session.add(
            WorkflowAuditLogModel(
                event_id=str(uuid4()),
                event_type=EVENT_TYPE_DRIFT,
                aggregate_id=project_id,
                aggregate_type="project",
                version=3,
                payload={"phase": "content", "version": 3},
                metadata_json={"project_id": project_id},
            )
        )
        await session.commit()

        post_change = await drill.snapshot_carousel_state(session, project_id)
        assert post_change is not None
        # Forward change is observable -> baseline differs from post-change.
        assert not drill.compare_snapshots(baseline, post_change).matched

        # --- restore-from-backup: revert row + drop the drift event ----------
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        model.workflow_status = WORKFLOW_STATUS_BASELINE
        model.phase_status = PHASE_STATUS_BASELINE
        model.lock_version = 3
        await session.execute(
            delete(WorkflowAuditLogModel).where(
                WorkflowAuditLogModel.event_type == EVENT_TYPE_DRIFT
            )
        )
        await session.commit()

        restored = await drill.snapshot_carousel_state(session, project_id)
        comparison = drill.compare_snapshots(baseline, restored)
        assert comparison.matched, comparison.differences

    @pytest.mark.asyncio
    async def test_incomplete_restore_is_detected(self, session: AsyncSession) -> None:
        """The smoke comparison flags residual drift after a partial restore."""
        drill = _load_drill()
        project_id = await _seed_baseline(session)
        baseline = await drill.snapshot_carousel_state(session, project_id)

        # Restore reverts scalar fields but FORGETS to drop the drift event.
        session.add(
            WorkflowAuditLogModel(
                event_id=str(uuid4()),
                event_type=EVENT_TYPE_DRIFT,
                aggregate_id=project_id,
                aggregate_type="project",
                version=3,
                payload={"phase": "content", "version": 3},
                metadata_json={"project_id": project_id},
            )
        )
        await session.commit()

        restored = await drill.snapshot_carousel_state(session, project_id)
        comparison = drill.compare_snapshots(baseline, restored)
        assert not comparison.matched
        assert any("audit_trace" in diff for diff in comparison.differences)

    @pytest.mark.asyncio
    async def test_dropped_project_is_detected(self, session: AsyncSession) -> None:
        """A restore that loses the project row entirely is flagged."""
        drill = _load_drill()
        project_id = await _seed_baseline(session)
        baseline = await drill.snapshot_carousel_state(session, project_id)

        restored = await drill.snapshot_carousel_state(session, str(uuid4()))
        assert restored is None
        comparison = drill.compare_snapshots(baseline, restored)
        assert not comparison.matched
        assert any("presence mismatch" in diff for diff in comparison.differences)
