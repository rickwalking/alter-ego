"""The autopilot queue bridge, the stepper adapter and the dead-letter notices.

SQLite with the full schema; the editorial engine is never reached because the
runs here are parked, finished or missing.
"""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_FAILED
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.modules.autopilot.bootstrap import AutopilotTickConfig
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.queue_bridge import AutopilotQueueBridge
from rag_backend.modules.generation_queue.infrastructure.drive_adapters import (
    AutopilotStepperAdapter,
)
from rag_backend.modules.generation_queue.infrastructure.notices import (
    OwnerDeadLetterNotices,
)
from tests.unit.modules.generation_queue.queue_fakes import make_run, resume_run

pytestmark = pytest.mark.integration

_NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
Sessions = async_sessionmaker[AsyncSession]


@pytest_asyncio.fixture(loop_scope="function")
async def sessions() -> AsyncIterator[Sessions]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    previous = db_config.c_engine
    db_config.c_engine = engine
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        db_config.c_engine = previous
        await engine.dispose()


def _bridge(sessions: Sessions) -> AutopilotQueueBridge:
    def no_engine() -> object:
        raise AssertionError("the engine must not be built")

    return AutopilotQueueBridge(
        config=AutopilotTickConfig(
            owner_user_id="owner",
            engine_factory=no_engine,
            stale_after_seconds=180,
        ),
        sessions=sessions,
        retryable=lambda _exc: False,
    )


async def _seed(
    sessions: Sessions, state: AutopilotRunState, project_id: str | None = None
) -> UUID:
    """Seed a run stamped with the current time.

    The bridge reads the system clock, so a run stamped with a fixed date ages past
    the review deadline as the calendar moves and the sweep starts expiring it.
    """
    topic_id, run_id = uuid4(), uuid4()
    seeded_at = datetime.now(UTC)
    async with sessions() as session:
        session.add(
            TopicCandidateModel(
                id=topic_id,
                title="T",
                angle="a",
                why_viral="w",
                audience="builders",
                niche="ai",
                brief="b",
                sources=["https://example.com/a"],
                score=10,
                signal_hash=uuid4().hex,
                status="accepted",
            )
        )
        await session.flush()
        session.add(
            AutopilotRunModel(
                id=run_id,
                topic_candidate_id=topic_id,
                carousel_project_id=project_id,
                state=state.value,
                publish_attempts=0,
                telegram_message_ids=[],
                created_at=seeded_at,
                updated_at=seeded_at,
            )
        )
        await session.commit()
    return run_id


async def _state(sessions: Sessions, run_id: UUID) -> tuple[str, str | None]:
    async with sessions() as session:
        row = await session.get(AutopilotRunModel, run_id)
        assert row is not None
        return row.state, row.state_reason


async def test_bridge_lists_only_runs_that_need_driving(sessions: Sessions) -> None:
    """Scenario: The dispatcher stages and hands over the queued work"""
    queued = await _seed(sessions, AutopilotRunState.QUEUED)
    reworking = await _seed(sessions, AutopilotRunState.REWORKING, "p2")
    await _seed(sessions, AutopilotRunState.AWAITING_OWNER, "p3")
    listed = await _bridge(sessions).active_run_ids(10)
    assert sorted(listed, key=str) == sorted(
        [(str(queued), None), (str(reworking), "p2")], key=str
    )


async def test_bridge_facts_and_no_step_for_a_parked_run(sessions: Sessions) -> None:
    """Scenario: One autopilot drive steps a run until the owner has to act"""
    bridge = _bridge(sessions)
    owner = await _seed(sessions, AutopilotRunState.AWAITING_OWNER, "p3")
    facts = await bridge.facts(str(owner))
    assert facts is not None
    assert (facts.state, facts.project_id) == ("awaiting_owner", "p3")
    assert await bridge.facts(str(uuid4())) is None
    assert await bridge.step(str(owner)) == 0
    assert await bridge.step(str(uuid4())) == 0
    assert await bridge.sweep() == 0


async def test_stepper_phase_keys(sessions: Sessions) -> None:
    """Scenario: A phase that keeps failing is parked once its budget is spent"""
    queued = await _seed(sessions, AutopilotRunState.QUEUED)
    generating = await _seed(sessions, AutopilotRunState.GENERATING, "p9")
    stepper = AutopilotStepperAdapter(_bridge(sessions), sessions)
    assert (await stepper.view(str(queued))).phase == "start"
    assert (await stepper.view(str(generating))).phase == "start"
    async with sessions() as session:
        session.add(
            CarouselProjectModel(
                id="p9",
                topic="T",
                audience="builders",
                niche="ai",
                current_phase="content",
                phase_status="awaiting_human",
            )
        )
        await session.commit()
    view = await stepper.view(str(generating))
    assert view is not None
    assert view.phase == "generating:content"
    assert await stepper.view(str(uuid4())) is None


async def test_dead_letter_parks_the_autopilot_run_with_one_notice(
    sessions: Sessions,
) -> None:
    """Scenario: A permanent failure parks the run with its reason"""
    run_id = await _seed(sessions, AutopilotRunState.GENERATING, "p5")
    notices = OwnerDeadLetterNotices(_bridge(sessions), sessions)
    run = make_run(autopilot_run_id=str(run_id))
    await notices.stage(run, "phase_budget_exhausted")
    assert await _state(sessions, run_id) == (
        "escalated",
        "queue_dead_letter:phase_budget_exhausted",
    )
    async with sessions() as session:
        events = (
            await session.scalars(
                select(EventOutboxModel.event_type).where(
                    EventOutboxModel.aggregate_id == str(run_id)
                )
            )
        ).all()
    assert list(events) == ["content.autopilot.state_changed"]
    await notices.stage(run, "phase_budget_exhausted")
    assert await _state(sessions, run_id) == (
        "escalated",
        "queue_dead_letter:phase_budget_exhausted",
    )


async def test_dead_letter_fails_the_dashboard_project(
    sessions: Sessions, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: A permanent failure parks the run with its reason"""
    from rag_backend.modules.generation_queue.infrastructure import notices as module

    finished: list[tuple[str, str]] = []

    async def record(project_id: str, reason: str, **_kwargs: object) -> None:
        finished.append((project_id, reason))

    monkeypatch.setattr(module, "publish_run_finished", record)
    async with sessions() as session:
        session.add(
            CarouselProjectModel(
                id="p1",
                topic="T",
                audience="builders",
                niche="ai",
                current_phase="outline",
                phase_status="in_progress",
            )
        )
        await session.commit()
    notices = OwnerDeadLetterNotices(_bridge(sessions), sessions)
    await notices.stage(resume_run(), "permanent")
    await notices.stage(resume_run(carousel_project_id=None), "permanent")
    async with sessions() as session:
        row = await session.get(CarouselProjectModel, "p1")
        assert row is not None
        assert row.phase_status == PHASE_STATUS_FAILED
    assert finished == [("p1", "failed")]


async def test_rollback_hands_queued_work_back(sessions: Sessions) -> None:
    """Scenario: A revert of the worker hands the queued work back"""
    from rag_backend.modules.generation_queue.domain.models import autopilot_stage
    from rag_backend.modules.generation_queue.infrastructure.models import (
        GenerationRunModel,
    )
    from rag_backend.modules.generation_queue.infrastructure.repository import (
        SqlGenerationRunStore,
    )
    from rag_backend.modules.generation_queue.public import (
        WorkflowResumePayload,
        count_queue_hand_back,
        hand_back_queue,
        stage_workflow_resume,
    )
    from rag_backend.scripts import generation_queue_rollback as rollback_cli

    async with sessions() as session:
        for project_id, status in (("q1", "in_progress"), ("q2", "in_progress")):
            session.add(
                CarouselProjectModel(
                    id=project_id,
                    topic="T",
                    audience="builders",
                    niche="ai",
                    current_phase="outline",
                    phase_status=status,
                )
            )
        await session.flush()
        await stage_workflow_resume(
            session,
            WorkflowResumePayload(project_id="q1", action="approve", reviewer_id="u1"),
            2,
        )
        await session.commit()
    await SqlGenerationRunStore(sessions).stage(autopilot_stage("r1"))
    engine = db_config.c_engine
    assert engine is not None
    pending = await count_queue_hand_back(engine)
    assert (pending.projects_released, pending.runs_cancelled) == (1, 2)
    code = await rollback_cli.run_modes(
        engine, argparse.Namespace(apply=False, verify=True)
    )
    assert code == rollback_cli.EXIT_OK
    report = await hand_back_queue(engine)
    assert (report.projects_released, report.runs_cancelled) == (1, 2)
    async with sessions() as session:
        q1 = await session.get(CarouselProjectModel, "q1")
        q2 = await session.get(CarouselProjectModel, "q2")
        statuses = (await session.scalars(select(GenerationRunModel.status))).all()
    assert q1 is not None
    assert q2 is not None
    assert (q1.phase_status, q2.phase_status) == ("awaiting_human", "in_progress")
    assert set(statuses) == {"cancelled"}
    again = await hand_back_queue(engine)
    assert (again.projects_released, again.runs_cancelled) == (0, 0)


async def test_a_redelivered_start_reuses_the_runs_carousel(sessions: Sessions) -> None:
    """Scenario: A run interrupted by a deploy resumes by itself"""
    from rag_backend.modules.autopilot.application.run_spec import autopilot_project_id
    from rag_backend.modules.autopilot.domain.gate import ProjectSpec
    from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
        EditorialDriverConfig,
        InProcessEditorialDriver,
    )

    run_id = uuid4()
    spec = ProjectSpec(
        topic="T",
        audience="devs",
        niche="ai",
        brief="b",
        sources=(),
        owner_user_id="",
        project_id=autopilot_project_id(run_id),
    )
    created: list[str] = []
    for _ in range(2):
        async with sessions() as session:
            driver = InProcessEditorialDriver(
                EditorialDriverConfig(
                    session=session,
                    engine_factory=lambda: None,
                    clock=type("Clock", (), {"now": staticmethod(lambda: _NOW)})(),
                    stale_after_seconds=180,
                )
            )
            created.append(await driver.create_project(spec))
            await session.commit()
    assert created == [autopilot_project_id(run_id)] * 2
    assert autopilot_project_id(run_id) == autopilot_project_id(run_id)
    assert autopilot_project_id(uuid4()) != autopilot_project_id(run_id)
    async with sessions() as session:
        rows = (await session.scalars(select(CarouselProjectModel.id))).all()
    assert list(rows) == [autopilot_project_id(run_id)]
