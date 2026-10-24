"""A phase killed mid-run resumes from the checkpoint through the queue's recovery.

Uses the real editorial engine, LangGraph graph and checkpointer of
``test_autopilot_resume_runs_phase`` (only the LLM artifacts are faked): the
content phase dies like a deploy killed it, the row stays ``in_progress``, and the
job that gets the drive lock reaps it and re-runs the parked node.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

import rag_backend.infrastructure.database.config as db_config
from rag_backend.infrastructure.database.carousel_run_reaper import (
    CarouselRunReaperConfig,
    CarouselRunReaperRepository,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.constants import (
    GATE_CONTENT,
    PHASE_STATUS_AWAITING,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.modules.generation_queue.application.executors import (
    RecoveryDependencies,
    WorkflowResumeDependencies,
    WorkflowResumeExecutor,
)
from rag_backend.modules.generation_queue.domain.models import (
    WorkflowResumePayload,
    adopt_stage,
)
from rag_backend.modules.generation_queue.domain.ports import StepOutcome
from rag_backend.modules.generation_queue.infrastructure.drive_adapters import (
    ProjectRecoveryAdapter,
    RecoveryConfig,
    WorkflowResumerAdapter,
)
from tests.integration.test_autopilot_resume_runs_phase import (
    _park_like_prod,
    _row,
    _World,
    world,
)
from tests.unit.modules.generation_queue.queue_fakes import FakeStore, resume_run

__all__ = ["world"]

pytestmark = pytest.mark.integration


def _recovery(service_world: _World) -> ProjectRecoveryAdapter:
    return ProjectRecoveryAdapter(
        RecoveryConfig(
            sessions=db_config.get_session_maker(),
            reaper=CarouselRunReaperRepository(
                CarouselRunReaperConfig(
                    heartbeat_stale_seconds=180,
                    reap_observations=3,
                    overdue_minutes=60,
                )
            ),
            engine_factory=lambda: service_world.service,
        )
    )


class _Tracker:
    async def begin(self, phase: str) -> None:
        del phase

    async def finish(self, phase: str) -> None:
        del phase


def _executor(world: _World) -> WorkflowResumeExecutor:
    return WorkflowResumeExecutor(
        WorkflowResumeDependencies(
            resumer=WorkflowResumerAdapter(lambda: world.service),
            recovery=RecoveryDependencies(store=FakeStore(), recovery=_recovery(world)),
        )
    )


async def _die_mid_content(world: _World) -> None:
    """The content phase was running when the container was killed."""
    await _park_like_prod(world)
    async with db_config.get_session_maker()() as session:
        await session.execute(
            update(CarouselProjectModel)
            .where(CarouselProjectModel.id == world.project_id)
            .values(
                phase_status=PHASE_STATUS_IN_PROGRESS,
                current_phase=GATE_CONTENT,
                run_started_at=datetime.now(UTC) - timedelta(minutes=10),
                run_heartbeat_at=datetime.now(UTC) - timedelta(minutes=8),
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_orphaned_phase_is_reaped_and_redriven(world: _World) -> None:
    """Scenario: A run interrupted by a deploy resumes by itself"""
    await _die_mid_content(world)
    recovery = _recovery(world)
    assert await recovery.in_progress(world.project_id)
    assert await recovery.current_phase(world.project_id) == GATE_CONTENT
    assert await recovery.reap(world.project_id)
    assert not await recovery.in_progress(world.project_id)
    assert await recovery.redrive_if_parked(world.project_id)
    assert world.llm.content_runs == 2
    row = await _row(world)
    assert row.current_phase == GATE_CONTENT
    assert row.phase_status == PHASE_STATUS_AWAITING
    assert not await recovery.redrive_if_parked(world.project_id)
    assert not await recovery.reap(world.project_id)
    assert await recovery.current_phase("missing") == ""
    assert not await recovery.redrive_if_parked("missing")


@pytest.mark.asyncio
async def test_repicked_resume_recovers_without_a_second_decision(
    world: _World,
) -> None:
    """Scenario: A re-picked dashboard resume does not re-apply the review decision"""
    await _die_mid_content(world)
    payload = WorkflowResumePayload(
        project_id=world.project_id, action="approve", reviewer_id="u1"
    )
    run = resume_run(
        payload=payload.dump(), carousel_project_id=world.project_id, last_phase="x"
    )
    assert await _executor(world).execute(run, _Tracker()) is StepOutcome.DONE
    assert world.llm.content_runs == 2
    state = await world.service.get_workflow_state(world.project_id)
    assert state is not None
    assert state.get("current_phase") == GATE_CONTENT
    assert not state.get("content_approved")


@pytest.mark.asyncio
async def test_adopted_project_recovers_without_a_decision(world: _World) -> None:
    """Scenario: A dashboard resume a deploy killed before the cutover resumes in the worker"""
    await _die_mid_content(world)
    stage = adopt_stage(world.project_id, "T")
    run = resume_run(
        dedupe_key=stage.dedupe_key,
        payload=stage.payload,
        carousel_project_id=world.project_id,
    )
    assert await _executor(world).execute(run, _Tracker()) is StepOutcome.DONE
    assert world.llm.content_runs == 2
    row = await _row(world)
    assert row.phase_status == PHASE_STATUS_AWAITING
    state = await world.service.get_workflow_state(world.project_id)
    assert state is not None
    assert not state.get("content_approved")
