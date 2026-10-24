"""Adapters from the executors' ports to the autopilot and editorial code.

Each call opens its own session and commits it: a drive runs for minutes and must
never hold a transaction across LLM or Chromium work.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.application.services.carousel import (
    editorial_workflow_resume_runner as resume_runner,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_NOTHING_TO_REDRIVE,
    ERR_RESUME_ALREADY_IN_PROGRESS,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.infrastructure.database.carousel_run_reaper import (
    CarouselRunReaperRepository,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.queue_bridge import AutopilotQueueBridge
from rag_backend.modules.editorial.public import AutomationRun, redrive_automation_phase
from rag_backend.modules.generation_queue.constants import PHASE_START
from rag_backend.modules.generation_queue.domain.drive_ports import AutopilotView
from rag_backend.modules.generation_queue.domain.models import WorkflowResumePayload

EngineFactory = Callable[[], EditorialWorkflowService]
SessionFactory = async_sessionmaker[AsyncSession]

_QUEUED = "queued"
_REDRIVE_REFUSALS = frozenset({
    ERR_NOTHING_TO_REDRIVE,
    ERR_RESUME_ALREADY_IN_PROGRESS,
    ERR_VERSION_CONFLICT,
})


@dataclass(frozen=True)
class _ProjectRow:
    phase: str
    phase_status: str
    lock_version: int


async def _project_row(sessions: SessionFactory, project_id: str) -> _ProjectRow | None:
    async with sessions() as session:
        result = await session.execute(
            select(
                CarouselProjectModel.current_phase,
                CarouselProjectModel.phase_status,
                CarouselProjectModel.lock_version,
            ).where(CarouselProjectModel.id == project_id)
        )
        row = result.one_or_none()
    if row is None:
        return None
    return _ProjectRow(
        phase=str(row[0] or ""),
        phase_status=str(row[1] or ""),
        lock_version=int(row[2] or 1),
    )


class AutopilotStepperAdapter:
    """``AutopilotStepper`` on the autopilot queue bridge."""

    def __init__(self, bridge: AutopilotQueueBridge, sessions: SessionFactory) -> None:
        self._bridge = bridge
        self._sessions = sessions

    async def view(self, run_id: str) -> AutopilotView | None:
        """State, project and phase key (``start`` until a project runs)."""
        facts = await self._bridge.facts(run_id)
        if facts is None:
            return None
        return AutopilotView(
            state=facts.state,
            project_id=facts.project_id,
            phase=await self._phase(facts.state, facts.project_id),
        )

    async def step(self, run_id: str) -> int:
        """One runner step for the run."""
        return await self._bridge.step(run_id)

    async def _phase(self, state: str, project_id: str | None) -> str:
        if state == _QUEUED or project_id is None:
            return PHASE_START
        row = await _project_row(self._sessions, project_id)
        if row is None or not row.phase:
            return PHASE_START
        return f"{state}:{row.phase}"


@dataclass(frozen=True, kw_only=True)
class RecoveryConfig:
    """What the project recovery reads and drives with."""

    sessions: SessionFactory
    reaper: CarouselRunReaperRepository
    engine_factory: EngineFactory


class ProjectRecoveryAdapter:
    """``ProjectRecovery`` on the reaper and the editorial re-drive."""

    def __init__(self, config: RecoveryConfig) -> None:
        self._config = config

    async def current_phase(self, project_id: str) -> str:
        """The project's current phase ('' when the project is unknown)."""
        row = await _project_row(self._config.sessions, project_id)
        return row.phase if row is not None else ""

    async def in_progress(self, project_id: str) -> bool:
        """The row says a phase is running."""
        row = await _project_row(self._config.sessions, project_id)
        return row is not None and row.phase_status == PHASE_STATUS_IN_PROGRESS

    async def reap(self, project_id: str) -> bool:
        """Fence and park the orphaned run now."""
        async with self._config.sessions() as session:
            reaped = await self._config.reaper.reap_orphan(session, project_id)
            await session.commit()
            return reaped

    async def redrive_if_parked(self, project_id: str) -> bool:
        """Re-run the node the checkpoint is parked before, once."""
        row = await _project_row(self._config.sessions, project_id)
        if row is None:
            return False
        async with self._config.sessions() as session:
            try:
                await redrive_automation_phase(
                    AutomationRun(
                        engine=self._config.engine_factory(),
                        session=session,
                        project_id=project_id,
                        expected_version=row.lock_version,
                        action="",
                    )
                )
            except ValueError as exc:
                if str(exc) in _REDRIVE_REFUSALS:
                    return False
                raise
            return True


class WorkflowResumerAdapter:
    """``WorkflowResumer`` on the run-owned resume wrapper the web used to schedule."""

    def __init__(self, engine_factory: EngineFactory) -> None:
        self._engine_factory = engine_factory

    async def resume(self, payload: WorkflowResumePayload) -> None:
        """Run the review decision inline (heartbeat, epoch fence, run events)."""
        await resume_runner.execute_resume_run(
            self._engine_factory(),
            resume_runner.BackgroundResumeParams(
                project_id=payload.project_id,
                action=payload.action,
                reviewer_id=payload.reviewer_id,
                feedback=payload.feedback,
                project_title=payload.project_title,
                structured_feedback=payload.structured_feedback,
            ),
        )


__all__ = [
    "AutopilotStepperAdapter",
    "EngineFactory",
    "ProjectRecoveryAdapter",
    "RecoveryConfig",
    "WorkflowResumerAdapter",
]
