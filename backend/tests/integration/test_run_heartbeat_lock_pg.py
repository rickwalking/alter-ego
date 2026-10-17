"""The run heartbeat is never blocked by the run's own phase sync (AE-0390).

Gherkin: tests/features/workflow_tracing_and_heartbeat.feature
  Scenario: The heartbeat succeeds while a phase run is in progress
  Scenario: The phase sync releases the project row before finalize, events and beats

Prod 2026-10-15, carousel f21b2bdb: ``carousel_run_heartbeat_failed`` /
``LockNotAvailableError`` twice per phase. The run flushed its phase-sync
UPDATE on ``carousel_projects`` and committed only at the very end, so the
review events, SSE and both stage beats (VALIDATING, PERSISTING) waited on
the run's own row lock until their 2 s ``lock_timeout``.

Real Postgres (two sessions), real ``EditorialWorkflowService``, LangGraph
graph, autopilot driver and run wrapper. Only the LLM artifact call is faked.
"""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services.carousel import (
    editorial_workflow_resume_runner as resume_runner,
)
from rag_backend.application.services.carousel import (
    editorial_workflow_run_heartbeat as run_heartbeat,
)
from rag_backend.application.services.carousel import (
    editorial_workflow_service as workflow_service,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_run import LOG_EVENT_RUN_HEARTBEAT_FAILED
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.infrastructure.database.pg_lock_timeout import (
    apply_run_write_lock_timeout,
)
from rag_backend.modules.autopilot.constants import GATE_OUTLINE
from rag_backend.modules.autopilot.domain.gate import (
    ProjectSpec,
    ResumeCommand,
    ResumeStatus,
)
from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
    EditorialDriverConfig,
    InProcessEditorialDriver,
)
from rag_backend.modules.editorial.public import write_run_heartbeat
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

pytestmark = [pytest.mark.integration, requires_postgres]

_OWNER = "owner-1"
_MODELS_PACKAGE = "rag_backend.infrastructure.database.models"
_BEAT_SECONDS = 0.05
_LLM_SECONDS = 0.4
_OUTLINE = [{"title": f"Slide {i}", "key_points": ["point"]} for i in range(7)]


class _Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass
class _Probe:
    """What a second session saw while the run held (or did not hold) the row."""

    llm_beats: list[bool] = field(default_factory=list)
    loop_beats: list[bool] = field(default_factory=list)
    after_sync: list[str] = field(default_factory=list)

    async def outline(self, state: CarouselWorkflowState) -> dict[str, object]:
        project_id = str(state.get("project_id", ""))
        await asyncio.sleep(_LLM_SECONDS)
        self.loop_beats.append(await _loop_has_beaten(project_id))
        self.llm_beats.append(await write_run_heartbeat(project_id, 0))
        return {"outline": list(_OUTLINE)}

    async def touch_row(self, project_id: str) -> None:
        """Second session, run lock timeout: the row must not be held."""
        async with db_config.get_session_maker()() as other:
            await apply_run_write_lock_timeout(other)
            try:
                await other.execute(
                    update(CarouselProjectModel)
                    .where(CarouselProjectModel.id == project_id)
                    .values(updated_at=datetime.now(UTC))
                )
                await other.commit()
                self.after_sync.append("updated")
            except DBAPIError as exc:
                await other.rollback()
                self.after_sync.append(type(exc.orig).__name__)


async def _loop_has_beaten(project_id: str) -> bool:
    async with db_config.get_session_maker()() as other:
        row = await other.get(CarouselProjectModel, project_id)
        assert row is not None
        started, beat = row.run_started_at, row.run_heartbeat_at
        return bool(started and beat and beat > started)


@dataclass
class _World:
    session: AsyncSession
    driver: InProcessEditorialDriver
    probe: _Probe
    project_id: str


# pytest.ini defaults async fixtures to the session loop; asyncpg connections
# are bound to the loop that opened them, so the fixture must share the test's.
@pytest_asyncio.fixture(loop_scope="function")
async def world(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_World]:
    # Register every model so the isolated schema has all the run's tables.
    importlib.import_module(_MODELS_PACKAGE)
    async with isolated_schema(list(Base.metadata.tables)) as engine:
        previous = db_config.c_engine
        db_config.c_engine = engine
        probe = _Probe()
        _patch_run(monkeypatch, probe)
        service = EditorialWorkflowService(
            EditorialWorkflowConfig(llm=MagicMock(), checkpointer=MemorySaver())
        )
        try:
            async with db_config.get_session_maker()() as session:
                driver = _driver(session, service)
                project_id = await _seed_research_gate(session, service, driver)
                yield _World(session, driver, probe, project_id)
        finally:
            db_config.c_engine = previous


def _patch_run(monkeypatch: pytest.MonkeyPatch, probe: _Probe) -> None:
    async def _ensure(
        _runner: PhaseArtifactRunner, state: CarouselWorkflowState
    ) -> dict[str, object]:
        if state.get("current_phase") != GATE_OUTLINE:
            return {}
        return await probe.outline(state)

    real_sse = workflow_service.publish_workflow_sse_updates

    async def _sse_then_probe(project_id: str, state: CarouselWorkflowState) -> None:
        # Runs after the phase sync, review events and finalize, before the
        # runner's VALIDATING / PERSISTING stage beats and its final commit.
        await probe.touch_row(project_id)
        await real_sse(project_id, state)

    monkeypatch.setattr(PhaseArtifactRunner, "ensure_for_phase", _ensure)
    monkeypatch.setattr(
        workflow_service, "publish_workflow_sse_updates", _sse_then_probe
    )
    monkeypatch.setattr(resume_runner, "publish_run_finished", AsyncMock())
    monkeypatch.setattr(
        run_heartbeat, "DEFAULT_RUN_HEARTBEAT_INTERVAL_SECONDS", _BEAT_SECONDS
    )


def _driver(
    session: AsyncSession, service: EditorialWorkflowService
) -> InProcessEditorialDriver:
    return InProcessEditorialDriver(
        EditorialDriverConfig(
            session=session,
            engine_factory=lambda: service,
            clock=_Clock(),
            stale_after_seconds=180,
        )
    )


async def _seed_research_gate(
    session: AsyncSession,
    service: EditorialWorkflowService,
    driver: InProcessEditorialDriver,
) -> str:
    session.add(
        UserModel(
            id=_OWNER,
            email="owner@example.com",
            full_name="Owner",
            hashed_password="hash",
            role=UserRole.EDITOR.value,
        )
    )
    await session.flush()
    project_id = await driver.create_project(
        ProjectSpec(
            topic="Agents that ship",
            audience="builders",
            niche="ai",
            brief="brief",
            sources=(),
            owner_user_id=_OWNER,
        )
    )
    await session.commit()
    await service._orchestrator.start(
        project_id,
        {"topic": "Agents that ship"},
        research_findings=[{"content": "finding"}],
    )
    return project_id


async def _approve_research(world: _World) -> ResumeStatus:
    gate = await world.driver.read_gate(world.project_id)
    await world.session.commit()
    result = await world.driver.resume(
        ResumeCommand(
            project_id=world.project_id,
            action="approve",
            expected_version=gate.lock_version,
            feedback="",
            phase=gate.phase,
        )
    )
    return result.status


# Scenario: The heartbeat succeeds while a phase run is in progress
@pytest.mark.asyncio
async def test_heartbeat_succeeds_while_the_outline_llm_runs(world: _World) -> None:
    status = await _approve_research(world)

    assert status is ResumeStatus.APPLIED
    assert world.probe.loop_beats == [True]
    # epoch 0 is the fresh row's epoch: the beat matched and stamped the row.
    assert world.probe.llm_beats == [True]


# Scenario: The phase sync releases the project row before finalize, events and beats
@pytest.mark.asyncio
async def test_phase_sync_never_blocks_the_heartbeat(world: _World) -> None:
    with capture_logs() as logs:
        status = await _approve_research(world)

    assert status is ResumeStatus.APPLIED
    assert world.probe.after_sync == ["updated"]
    failed = [log for log in logs if log.get("event") == LOG_EVENT_RUN_HEARTBEAT_FAILED]
    assert failed == []
    async with db_config.get_session_maker()() as other:
        row = await other.get(CarouselProjectModel, world.project_id)
        assert row is not None
        assert (row.current_phase, row.phase_status) == (GATE_OUTLINE, "awaiting_human")
