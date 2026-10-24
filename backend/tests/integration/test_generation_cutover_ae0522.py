"""The deploy one-shot queues a recovery for projects a dead driver left behind."""

from __future__ import annotations

import argparse
import hashlib
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.generation_queue.domain.models import (
    WorkflowResumePayload,
    autopilot_stage,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.repository import (
    SqlGenerationRunStore,
)
from rag_backend.modules.generation_queue.public import (
    adopt_orphaned_projects,
    hold_project_drive,
)
from rag_backend.scripts import generation_queue_schema as cli
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

pytestmark = [pytest.mark.integration, requires_postgres]

_TABLES = (
    "users",
    "persona_profiles",
    "quality_rubrics",
    "carousel_creator_assets",
    "carousel_projects",
    "topic_candidates",
    "autopilot_runs",
    "generation_runs",
)


@pytest_asyncio.fixture(loop_scope="function")
async def engine() -> AsyncIterator[AsyncEngine]:
    async with isolated_schema(_TABLES) as scoped:
        yield scoped


def _project(project_id: str, phase_status: str) -> CarouselProjectModel:
    return CarouselProjectModel(
        id=project_id,
        title=f"Title {project_id}",
        topic="T",
        audience="A",
        niche="N",
        phase_status=phase_status,
    )


def _autopilot_run(
    project_id: str, now: datetime
) -> tuple[TopicCandidateModel, AutopilotRunModel]:
    topic = TopicCandidateModel(
        id=uuid.uuid4(),
        title="Topic",
        angle="Angle",
        why_viral="Why",
        audience="devs",
        niche="ai",
        brief="Brief",
        sources=[],
        score=90,
        signal_hash=hashlib.sha256(project_id.encode()).hexdigest(),
        status="accepted",
        created_at=now,
    )
    run = AutopilotRunModel(
        id=uuid.uuid4(),
        topic_candidate_id=topic.id,
        carousel_project_id=project_id,
        state="drafting",
        publish_attempts=0,
        start_attempts=0,
        telegram_message_ids=[],
        created_at=now,
        updated_at=now,
    )
    return topic, run


async def _seed(sessions: async_sessionmaker[AsyncSession]) -> None:
    now = datetime.now(UTC)
    async with sessions() as session:
        session.add_all([
            _project("orphan", PHASE_STATUS_IN_PROGRESS),
            _project("queued", PHASE_STATUS_IN_PROGRESS),
            _project("autopilot", PHASE_STATUS_IN_PROGRESS),
            _project("driven", PHASE_STATUS_IN_PROGRESS),
            _project("parked", PHASE_STATUS_AWAITING_HUMAN),
        ])
        await session.flush()
        topic, run = _autopilot_run("autopilot", now)
        session.add(topic)
        await session.flush()
        session.add(run)
        await session.commit()
    await SqlGenerationRunStore(sessions).stage(autopilot_stage("r1", "queued"))


async def _adoptions(sessions: async_sessionmaker[AsyncSession]) -> list[str]:
    async with sessions() as session:
        rows = await session.scalars(
            select(GenerationRunModel).where(
                GenerationRunModel.dedupe_key.like("adopt:%")
            )
        )
        return [row.dedupe_key for row in rows.all()]


async def test_only_projects_nobody_drives_are_adopted(engine: AsyncEngine) -> None:
    """Scenario: A dashboard resume a deploy killed before the cutover resumes in the worker"""
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    await _seed(sessions)
    async with sessions() as session, hold_project_drive(session, "driven"):
        adopted = await adopt_orphaned_projects(engine)
    assert adopted == 1
    assert await _adoptions(sessions) == ["adopt:orphan"]
    queued = await SqlGenerationRunStore(sessions).undispatched(10)
    assert [run.dedupe_key for run in queued] == ["autopilot:r1", "adopt:orphan"]
    async with sessions() as session:
        row = await session.scalar(
            select(GenerationRunModel).where(
                GenerationRunModel.dedupe_key == "adopt:orphan"
            )
        )
    assert row is not None
    payload = WorkflowResumePayload.parse(row.payload)
    assert payload.action == "adopt"
    assert payload.project_title == "Title orphan"
    assert row.carousel_project_id == "orphan"


async def test_a_second_one_shot_queues_no_second_recovery(
    engine: AsyncEngine,
) -> None:
    """Scenario: A dashboard resume a deploy killed before the cutover resumes in the worker"""
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    await _seed(sessions)
    code = await cli.run_modes(engine, argparse.Namespace(apply=True, verify=True))
    again = await adopt_orphaned_projects(engine)
    assert code == cli.EXIT_OK
    assert again == 0
    assert sorted(await _adoptions(sessions)) == ["adopt:driven", "adopt:orphan"]
