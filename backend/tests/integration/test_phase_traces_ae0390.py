"""Every resumed phase LLM call runs in a named, tagged trace (AE-0390).

Gherkin: tests/features/workflow_tracing_and_heartbeat.feature

Prod 2026-10-15, autopilot carousel f21b2bdb: 10 GLM generations in 3 traces,
metadata only on ``workflow_research``, no tags anywhere. These tests use the
real ``EditorialWorkflowService``, LangGraph graph, run wrapper and autopilot
driver on a file SQLite database. The Langfuse client is a recording fake and
the phase LLM call is a fake that notes which trace it ran in.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.agents.carousel_editorial_orchestrator import (
    CarouselEditorialOrchestrator,
)
from rag_backend.application.services.carousel import (
    editorial_workflow_resume_runner as resume_runner,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    WORKFLOW_METADATA_EDITORIAL_7_PHASE,
)
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.modules.autopilot.constants import GATE_RESEARCH
from rag_backend.modules.autopilot.domain.gate import (
    ProjectSpec,
    ResumeCommand,
    ResumeStatus,
    StartCommand,
)
from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
    EditorialDriverConfig,
    InProcessEditorialDriver,
    StartStatus,
)
from tests.langfuse_trace_fakes import (
    RecordedTrace,
    TraceCollector,
    install_trace_collector,
)

_OWNER = "owner-1"
_REVIEWER = "reviewer-9"
_SLIDES = 7
_OUTLINE = [{"title": f"Slide {i}", "key_points": ["point"]} for i in range(_SLIDES)]
_DRAFTS = [{"draft_text": f"Draft {i}"} for i in range(_SLIDES)]
_ARTIFACTS: dict[str, dict[str, object]] = {
    "outline": {"outline": _OUTLINE},
    "content": {"slide_drafts": _DRAFTS},
}


class _Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass
class _Llm:
    """Fake phase LLM: records the trace each call ran in."""

    collector: TraceCollector
    calls: list[tuple[str, RecordedTrace | None]] = field(default_factory=list)

    async def ensure(self, state: CarouselWorkflowState) -> dict[str, object]:
        phase = str(state.get("current_phase", ""))
        self.calls.append((phase, self.collector.current()))
        return dict(_ARTIFACTS.get(phase, {}))

    def trace_of(self, phase: str) -> RecordedTrace:
        # A gate resume re-enters the node, so a phase can be seen twice;
        # every call must be traced, and each in its own phase trace.
        traces = [trace for seen, trace in self.calls if seen == phase]
        assert traces, self.calls
        assert None not in traces, f"{phase} LLM call ran outside any trace"
        named = {trace.name for trace in traces if trace is not None}
        assert named == {f"workflow_{phase}"}, named
        first = traces[0]
        assert first is not None
        return first


@dataclass
class _World:
    session: AsyncSession
    service: EditorialWorkflowService
    driver: InProcessEditorialDriver
    llm: _Llm
    project_id: str


@pytest_asyncio.fixture
async def world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[_World]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ae0390.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    previous = db_config.c_engine
    db_config.c_engine = engine
    llm = _Llm(collector=install_trace_collector(monkeypatch))

    async def _ensure(
        _runner: PhaseArtifactRunner, state: CarouselWorkflowState
    ) -> dict[str, object]:
        return await llm.ensure(state)

    monkeypatch.setattr(PhaseArtifactRunner, "ensure_for_phase", _ensure)
    monkeypatch.setattr(resume_runner, "publish_run_finished", AsyncMock())
    # SQLite has no lock_timeout; the interval loop is not under test here.
    monkeypatch.setattr(
        resume_runner, "write_run_heartbeat_once", AsyncMock(return_value=True)
    )
    service = EditorialWorkflowService(
        EditorialWorkflowConfig(llm=MagicMock(), checkpointer=MemorySaver())
    )
    try:
        async with db_config.get_session_maker()() as session:
            driver = InProcessEditorialDriver(
                EditorialDriverConfig(
                    session=session,
                    engine_factory=lambda: service,
                    clock=_Clock(),
                    stale_after_seconds=180,
                )
            )
            project_id = await _seed_project(session, driver)
            yield _World(session, service, driver, llm, project_id)
    finally:
        db_config.c_engine = previous
        await engine.dispose()


async def _seed_project(session: AsyncSession, driver: InProcessEditorialDriver) -> str:
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
    project_id = await driver.create_project(_spec())
    await session.commit()
    return project_id


def _spec() -> ProjectSpec:
    return ProjectSpec(
        topic="Agents that ship",
        audience="builders",
        niche="ai",
        brief="brief",
        sources=(),
        owner_user_id=_OWNER,
    )


async def _park_at_research(world: _World) -> None:
    await world.service._orchestrator.start(
        world.project_id,
        {"topic": "Agents that ship"},
        research_findings=[{"content": "finding"}],
    )


async def _http_approve(world: _World) -> None:
    """What the HTTP route schedules after its in_progress commit."""
    await resume_runner.execute_resume_run(
        world.service,
        resume_runner.BackgroundResumeParams(
            project_id=world.project_id,
            action="approve",
            reviewer_id=_REVIEWER,
            feedback=None,
            project_title="Agents that ship",
            structured_feedback=None,
        ),
    )


def _assert_phase_trace(
    trace: RecordedTrace,
    phase: str,
    agent: str,
    *,
    extra_metadata: Mapping[str, str] | None = None,
) -> None:
    project_id = trace.metadata["project_id"]
    assert project_id != "unknown"
    assert trace.name == trace.trace_name == f"workflow_{phase}"
    expected_metadata = {
        "project_id": project_id,
        "phase": phase,
        "agent_name": agent,
        "user_id": _OWNER,
        "content_type": "carousel",
        **(extra_metadata or {}),
    }
    assert trace.metadata == expected_metadata
    assert trace.user_id == _OWNER
    assert trace.tags == [f"phase:{phase}", f"agent:{agent}", "content:carousel"]
    assert trace.propagated["tags"] == trace.tags
    assert trace.propagated["metadata"] == trace.metadata


# Scenario Outline: A resumed phase runs its LLM calls in a named, tagged trace
@pytest.mark.asyncio
async def test_http_resumes_trace_outline_then_content(world: _World) -> None:
    await _park_at_research(world)

    await _http_approve(world)
    await _http_approve(world)

    _assert_phase_trace(world.llm.trace_of("outline"), "outline", "editorial_workflow")
    _assert_phase_trace(world.llm.trace_of("content"), "content", "editorial_workflow")
    assert world.llm.trace_of("outline").metadata["project_id"] == world.project_id


# Scenario: The autopilot run traces its phases as the autopilot agent
@pytest.mark.asyncio
async def test_autopilot_resume_traces_the_outline_as_autopilot(world: _World) -> None:
    await _park_at_research(world)
    gate = await world.driver.read_gate(world.project_id)

    result = await world.driver.resume(
        ResumeCommand(
            project_id=world.project_id,
            action="approve",
            expected_version=gate.lock_version,
            feedback="",
            phase=gate.phase,
        )
    )

    assert result.status is ResumeStatus.APPLIED
    _assert_phase_trace(world.llm.trace_of("outline"), "outline", "autopilot")


# Scenario: Research synthesis at workflow start is traced with the creator
@pytest.mark.asyncio
async def test_autopilot_start_traces_research_as_autopilot(
    world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[RecordedTrace | None] = []

    async def _synthesize(
        _orchestrator: CarouselEditorialOrchestrator, _sources: object
    ) -> list[dict[str, object]]:
        seen.append(world.llm.collector.current())
        return [{"content": "finding"}]

    monkeypatch.setattr(
        CarouselEditorialOrchestrator, "synthesize_research", _synthesize
    )

    status = await world.driver.start(
        StartCommand(project_id=world.project_id, spec=_spec(), phase=GATE_RESEARCH)
    )

    assert status is StartStatus.STARTED
    assert len(seen) == 1
    assert seen[0] is not None
    _assert_phase_trace(
        seen[0],
        "research",
        "autopilot",
        extra_metadata={"workflow": WORKFLOW_METADATA_EDITORIAL_7_PHASE},
    )


@pytest.mark.asyncio
async def test_http_start_traces_research_with_the_creator(
    world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[RecordedTrace | None] = []

    async def _synthesize(
        _orchestrator: CarouselEditorialOrchestrator, _sources: object
    ) -> list[dict[str, object]]:
        seen.append(world.llm.collector.current())
        return []

    monkeypatch.setattr(
        CarouselEditorialOrchestrator, "synthesize_research", _synthesize
    )

    await world.service.start_workflow(
        world.project_id,
        EditorialWorkflowStartInput(
            topic="Agents that ship",
            audience="builders",
            brief="brief",
            sources=[],
            user_id=_OWNER,
        ),
    )

    assert seen[0] is not None
    _assert_phase_trace(
        seen[0],
        "research",
        "editorial_workflow",
        extra_metadata={"workflow": WORKFLOW_METADATA_EDITORIAL_7_PHASE},
    )
