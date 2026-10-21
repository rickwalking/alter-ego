"""An autopilot approve runs the next phase for real.

Feature: autopilot_runner.feature (resume scenarios)

Prod 2026-10-14, carousel 8e350d6e: the runner approved the outline inside
the worker tick. The checkpointer committed the approved gate, the content
phase hit a provider error, and the driver turned it into a silent
``provider_outage`` and rolled the tick back. The checkpoint stayed at
``content/approved`` before a node nothing would run again, the row stayed at
``outline/awaiting_human`` with no run, and the policy waited forever.

These tests use the real ``EditorialWorkflowService``, LangGraph graph,
checkpointer interrupts, run wrapper, and a file SQLite database (separate
connections, so an open tick transaction would block the run's commit). Only
the LLM artifact generation is faked.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import httpx
import openai
import pytest
import pytest_asyncio
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services.carousel import (
    editorial_workflow_resume_runner as resume_runner,
)
from rag_backend.application.services.carousel import (
    editorial_workflow_run_heartbeat as run_heartbeat,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    ResumeWorkflowInput,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.modules.autopilot.constants import (
    GATE_CONTENT,
    GATE_OUTLINE,
    PHASE_STATUS_AWAITING,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    REASON_PHASE_FAILED,
    REASON_WAITING,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateAction,
    ProjectSpec,
    RedriveCommand,
    ResumeCommand,
    ResumeStatus,
)
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
    EditorialDriverConfig,
    InProcessEditorialDriver,
)
from rag_backend.modules.autopilot.parked_constants import (
    PARKED_GRACE_SECONDS,
    REASON_ENGINE_PARKED,
)

_OWNER = "autopilot-owner"
_BEAT_SECONDS = 0.02
_SCRIPT = "redrive_parked_carousel.py"
_SECOND_RUN = 2
_EXIT_REFUSED = 3
_LLM_SECONDS = 0.3
_SLIDES = 7
_OUTLINE = [{"title": f"Slide {i}", "key_points": ["point"]} for i in range(_SLIDES)]
_DRAFTS = [{"draft_text": f"Draft {i}"} for i in range(_SLIDES)]


class _Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass
class _Llm:
    """Fake artifact generation. Records what the run saw mid-phase."""

    fail_content: bool = False
    content_runs: int = 0
    seen_rows: list[tuple[str, bool, bool]] = field(default_factory=list)
    beats: list[bool] = field(default_factory=list)
    tick_in_transaction: list[bool] = field(default_factory=list)
    tick: AsyncSession | None = None

    async def ensure(self, state: CarouselWorkflowState) -> dict[str, object]:
        phase = state.get("current_phase")
        if phase == GATE_OUTLINE:
            return {"outline": list(_OUTLINE)}
        if phase != GATE_CONTENT:
            return {}
        self.content_runs += 1
        project_id = str(state.get("project_id", ""))
        await self._observe(project_id)
        await asyncio.sleep(_LLM_SECONDS)
        await self._observe_beat(project_id)
        if self.fail_content:
            request = httpx.Request("POST", "https://llm.example/v1/chat")
            raise openai.APITimeoutError(request=request)
        return {"slide_drafts": list(_DRAFTS)}

    async def _observe(self, project_id: str) -> None:
        if self.tick is not None:
            self.tick_in_transaction.append(self.tick.in_transaction())
        async with db_config.get_session_maker()() as other:
            row = await other.get(CarouselProjectModel, project_id)
            assert row is not None
            self.seen_rows.append((
                str(row.phase_status),
                row.run_started_at is not None,
                row.run_heartbeat_at is not None,
            ))

    async def _observe_beat(self, project_id: str) -> None:
        """The interval heartbeat loop refreshed the row while the LLM ran."""
        async with db_config.get_session_maker()() as other:
            row = await other.get(CarouselProjectModel, project_id)
            assert row is not None
            started = row.run_started_at
            beat = row.run_heartbeat_at
            self.beats.append(bool(started and beat and beat > started))


@dataclass
class _World:
    session: AsyncSession
    service: EditorialWorkflowService
    driver: InProcessEditorialDriver
    llm: _Llm
    project_id: str
    finished: list[str]


@pytest_asyncio.fixture
async def world(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[_World]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ae0363.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    previous = db_config.c_engine
    db_config.c_engine = engine
    llm = _Llm()

    async def _ensure(
        _runner: PhaseArtifactRunner,
        state: CarouselWorkflowState,
    ) -> dict[str, object]:
        return await llm.ensure(state)

    finished: list[str] = []

    async def _finished(project_id: str, reason: str, **_kwargs: object) -> None:
        del project_id
        finished.append(reason)

    async def _stage_beat(project_id: str, epoch: int) -> bool:
        """SQLite has no lock_timeout: the inline stage beat would wait out the busy
        timeout behind the run's own flushed row. The interval loop still writes the
        real heartbeat.
        """
        del project_id, epoch
        return True

    monkeypatch.setattr(PhaseArtifactRunner, "ensure_for_phase", _ensure)
    monkeypatch.setattr(resume_runner, "publish_run_finished", _finished)
    monkeypatch.setattr(resume_runner, "write_run_heartbeat_once", _stage_beat)
    monkeypatch.setattr(
        run_heartbeat, "DEFAULT_RUN_HEARTBEAT_INTERVAL_SECONDS", _BEAT_SECONDS
    )
    service = EditorialWorkflowService(
        EditorialWorkflowConfig(llm=MagicMock(), checkpointer=MemorySaver())
    )
    try:
        async with db_config.get_session_maker()() as session:
            llm.tick = session
            driver = _driver(session, service)
            project_id = await _seed_outline_gate(session, service, driver)
            yield _World(
                session=session,
                service=service,
                driver=driver,
                llm=llm,
                project_id=project_id,
                finished=finished,
            )
    finally:
        db_config.c_engine = previous
        await engine.dispose()


def _driver(
    session: AsyncSession,
    service: EditorialWorkflowService,
) -> InProcessEditorialDriver:
    return InProcessEditorialDriver(
        EditorialDriverConfig(
            session=session,
            engine_factory=lambda: service,
            clock=_Clock(),
            stale_after_seconds=180,
        )
    )


async def _seed_outline_gate(
    session: AsyncSession,
    service: EditorialWorkflowService,
    driver: InProcessEditorialDriver,
) -> str:
    """A carousel parked at the outline gate, the way the runner left it."""
    session.add(
        UserModel(
            id=_OWNER,
            email="autopilot@example.com",
            full_name="Autopilot",
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
    await service._orchestrator.start(
        project_id,
        {"topic": "Agents that ship"},
        research_findings=[{"content": "finding"}],
    )
    await service.resume_workflow(
        ResumeWorkflowInput(
            project_id=project_id,
            action="approve",
            reviewer_id="",
            db=session,
        )
    )
    await session.commit()
    return project_id


async def _row(world: _World) -> CarouselProjectModel:
    async with db_config.get_session_maker()() as other:
        row = await other.get(CarouselProjectModel, world.project_id)
        assert row is not None
        return row


async def _approve(world: _World) -> ResumeStatus:
    gate = await world.driver.read_gate(world.project_id)
    assert gate.phase == GATE_OUTLINE
    assert decide(gate).action is GateAction.APPROVE
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


async def _park_like_prod(world: _World) -> None:
    """Reproduce the old in-tick resume that died mid content phase."""
    world.llm.fail_content = True
    with pytest.raises(openai.APITimeoutError):
        await world.service.resume_workflow(
            ResumeWorkflowInput(
                project_id=world.project_id,
                action="approve",
                reviewer_id="",
                db=world.session,
            )
        )
    await world.session.rollback()
    world.llm.fail_content = False


async def _age_row(world: _World, seconds: int) -> None:
    async with db_config.get_session_maker()() as other:
        await other.execute(
            update(CarouselProjectModel)
            .where(CarouselProjectModel.id == world.project_id)
            .values(updated_at=datetime.now(UTC) - timedelta(seconds=seconds))
        )
        await other.commit()


@pytest.mark.asyncio
async def test_approve_of_outline_runs_the_content_phase(world: _World) -> None:
    """Scenario: An autopilot approve of the outline runs the content phase."""
    before = await _row(world)

    status = await _approve(world)

    assert status is ResumeStatus.APPLIED
    assert world.llm.content_runs == 1
    state = await world.service.get_workflow_state(world.project_id)
    assert state is not None
    assert state.get("current_phase") == GATE_CONTENT
    assert state.get("phase_status") == PHASE_STATUS_AWAITING
    assert len(state.get("slide_drafts") or []) == _SLIDES
    assert not state.get("content_approved")
    after = await _row(world)
    assert after.current_phase == GATE_CONTENT
    assert after.phase_status == PHASE_STATUS_AWAITING
    assert after.lock_version == before.lock_version + 1
    assert after.run_started_at is None
    assert world.finished == ["completed"]
    gate = await world.driver.read_gate(world.project_id)
    assert gate.phase == GATE_CONTENT
    assert gate.parked is False


@pytest.mark.asyncio
async def test_phase_runs_with_a_heartbeat_and_no_open_tick_transaction(
    world: _World,
) -> None:
    """Scenario: The phase runs with a live run and a committed lock bump."""
    await _approve(world)

    assert world.llm.seen_rows == [(PHASE_STATUS_IN_PROGRESS, True, True)]
    assert world.llm.beats == [True]
    assert world.llm.tick_in_transaction == [False]


@pytest.mark.asyncio
async def test_failed_phase_escalates_instead_of_waiting(world: _World) -> None:
    """Scenario: A provider error in the next phase escalates, never parks."""
    world.llm.fail_content = True

    status = await _approve(world)

    assert status is ResumeStatus.APPLIED
    row = await _row(world)
    assert row.phase_status == PHASE_STATUS_FAILED
    assert world.finished == ["failed"]
    gate = await world.driver.read_gate(world.project_id)
    decision = decide(gate)
    assert decision.action is GateAction.ESCALATE
    assert decision.reason == REASON_PHASE_FAILED


@pytest.mark.asyncio
async def test_parked_workflow_waits_inside_the_grace_period(world: _World) -> None:
    """Scenario: A freshly parked workflow waits for the grace period."""
    await _park_like_prod(world)

    gate = await world.driver.read_gate(world.project_id)

    assert gate.phase == GATE_CONTENT
    assert gate.parked is True
    assert gate.parked_overdue is False
    assert decide(gate).reason == REASON_WAITING


@pytest.mark.asyncio
async def test_parked_workflow_is_redriven_to_its_own_gate(world: _World) -> None:
    """Scenario: A parked workflow past the grace period is re-driven.

    The re-drive sends no review: the content gate still needs one.
    """
    await _park_like_prod(world)
    await _age_row(world, PARKED_GRACE_SECONDS + 60)
    row = await _row(world)
    assert (row.current_phase, row.phase_status) == (
        GATE_OUTLINE,
        PHASE_STATUS_AWAITING,
    )

    gate = await world.driver.read_gate(world.project_id)
    decision = decide(gate)
    assert decision.action is GateAction.REDRIVE
    assert decision.reason == REASON_ENGINE_PARKED
    result = await world.driver.redrive(
        RedriveCommand(
            project_id=world.project_id,
            expected_version=gate.lock_version,
            phase=gate.phase,
        )
    )

    assert result.status is ResumeStatus.APPLIED
    state = await world.service.get_workflow_state(world.project_id)
    assert state is not None
    assert state.get("current_phase") == GATE_CONTENT
    assert state.get("phase_status") == PHASE_STATUS_AWAITING
    assert len(state.get("slide_drafts") or []) == _SLIDES
    assert not state.get("content_approved")
    assert world.llm.seen_rows[-1] == (PHASE_STATUS_IN_PROGRESS, True, True)
    after = await _row(world)
    assert (after.current_phase, after.phase_status) == (
        GATE_CONTENT,
        PHASE_STATUS_AWAITING,
    )


@pytest.mark.asyncio
async def test_redrive_without_a_parked_node_changes_nothing(world: _World) -> None:
    """Scenario: A re-drive with nothing parked is refused before any write."""
    before = await _row(world)

    result = await world.driver.redrive(
        RedriveCommand(
            project_id=world.project_id,
            expected_version=before.lock_version,
            phase=GATE_OUTLINE,
        )
    )

    assert result.status is ResumeStatus.NOT_PARKED
    after = await _row(world)
    assert after.lock_version == before.lock_version
    assert after.phase_status == PHASE_STATUS_AWAITING


@pytest.mark.asyncio
async def test_run_in_flight_waits_and_refuses_a_second_resume(world: _World) -> None:
    """Scenario: A carousel with a run in flight is never resumed twice."""
    async with db_config.get_session_maker()() as other:
        row = await other.get(CarouselProjectModel, world.project_id)
        assert row is not None
        row.phase_status = PHASE_STATUS_IN_PROGRESS
        await other.commit()
    gate = await world.driver.read_gate(world.project_id)
    assert decide(gate).action is GateAction.WAIT

    result = await world.driver.resume(
        ResumeCommand(
            project_id=world.project_id,
            action="approve",
            expected_version=gate.lock_version,
            feedback="",
            phase=GATE_OUTLINE,
        )
    )

    assert result.status is ResumeStatus.IN_PROGRESS
    assert world.llm.content_runs == 0


@pytest.mark.asyncio
async def test_revise_reruns_the_phase_and_cap_is_refused_up_front(
    world: _World,
) -> None:
    """Scenario: A revise re-runs the phase; a capped revise changes nothing."""
    gate = await world.driver.read_gate(world.project_id)
    revised = await world.driver.resume(
        ResumeCommand(
            project_id=world.project_id,
            action="revise",
            expected_version=gate.lock_version,
            feedback="shorter",
            phase=gate.phase,
        )
    )
    assert revised.status is ResumeStatus.APPLIED
    again = await world.driver.read_gate(world.project_id)
    assert (again.phase, again.phase_status) == (GATE_OUTLINE, PHASE_STATUS_AWAITING)
    assert again.lock_version == gate.lock_version + 1

    await world.service.update_workflow_state(
        world.project_id, {"revision_count": {GATE_OUTLINE: 99}}
    )
    capped = await world.driver.resume(
        ResumeCommand(
            project_id=world.project_id,
            action="revise",
            expected_version=again.lock_version,
            feedback="again",
            phase=GATE_OUTLINE,
        )
    )
    assert capped.status is ResumeStatus.REVISION_CAP
    row = await _row(world)
    assert row.phase_status == PHASE_STATUS_AWAITING
    assert row.lock_version == again.lock_version


def _recovery_script() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / _SCRIPT
    spec = importlib.util.spec_from_file_location("redrive_parked_carousel", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_recovery_script_dry_run_then_apply(
    world: _World,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Scenario: The ops script re-drives carousel 8e350d6e's parked phase."""
    script = _recovery_script()
    await _park_like_prod(world)

    dry = await script._redrive(
        world.service, script._Request(project_id=world.project_id, apply=False)
    )
    assert dry == 0
    assert world.llm.content_runs == 1
    assert "parked_before_node=True run_in_flight=False" in capsys.readouterr().out

    applied = await script._redrive(
        world.service, script._Request(project_id=world.project_id, apply=True)
    )
    assert applied == 0
    assert world.llm.content_runs == _SECOND_RUN
    state = await world.service.get_workflow_state(world.project_id)
    assert state is not None
    assert (state.get("current_phase"), state.get("phase_status")) == (
        GATE_CONTENT,
        PHASE_STATUS_AWAITING,
    )
    assert not state.get("content_approved")

    again = await script._redrive(
        world.service, script._Request(project_id=world.project_id, apply=True)
    )
    assert again == _EXIT_REFUSED
    assert script._parse(["x"]) is None
    assert script._parse(["x", "id", "--nope"]) is None
