"""The two kinds of generation work.

``AutopilotDriveExecutor`` steps one autopilot run until it waits for the owner or
ends, so approved themes are generated one after another rather than phase by
phase in turns. ``WorkflowResumeExecutor`` runs a dashboard approve or revise.

Both hold the drive lock (taken by the handler) while they run, so a project row
found ``in_progress`` when they start belongs to a driver that died (deploy, OOM,
kill): unless another queued run owns that phase, it is reaped at once and the
node the checkpoint is parked before is re-run. That is how a run interrupted by a
deploy resumes by itself instead of escalating as ``run_stale``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import structlog

from rag_backend.modules.generation_queue.constants import (
    ACTION_ADOPT,
    ERROR_BAD_PAYLOAD,
    LOG_ORPHAN_REAPED,
    MAX_STEPS_PER_JOB,
    PHASE_START,
)
from rag_backend.modules.generation_queue.domain.drive_ports import (
    AutopilotStepper,
    ProjectRecovery,
    WorkflowResumer,
)
from rag_backend.modules.generation_queue.domain.errors import (
    PermanentGenerationError,
)
from rag_backend.modules.generation_queue.domain.models import (
    AutopilotDrivePayload,
    GenerationRun,
    WorkflowResumePayload,
)
from rag_backend.modules.generation_queue.domain.ports import (
    GenerationRunStore,
    StepOutcome,
    StepTracker,
)

logger = structlog.get_logger()

DRIVEABLE_STATES = frozenset({"queued", "generating", "reworking"})
AUTOPILOT_KEY = "autopilot:{run_id}"
PROJECT_KEY = "project:{project_id}"
RECOVERY_PHASE = "recovery:{phase}"

Stopping = Callable[[], bool]


def project_key(project_id: str) -> str:
    """The drive-lock key of a carousel project."""
    return PROJECT_KEY.format(project_id=project_id)


@dataclass(frozen=True, kw_only=True)
class RecoveryDependencies:
    """What the orphan recovery reads and writes."""

    store: GenerationRunStore
    recovery: ProjectRecovery


async def recover_orphan(
    deps: RecoveryDependencies, run: GenerationRun, project_id: str
) -> bool:
    """Reap a project left ``in_progress`` by a dead driver. False when owned."""
    if not await deps.recovery.in_progress(project_id):
        return True
    if await deps.store.other_active_for_project(project_id, run.id):
        return False
    await deps.recovery.reap(project_id)
    logger.warning(
        LOG_ORPHAN_REAPED, generation_run_id=str(run.id), project_id=project_id
    )
    return True


async def redrive_parked(
    deps: RecoveryDependencies, tracker: StepTracker, project_id: str
) -> None:
    """Re-run a parked node, counted against its own recovery phase budget."""
    phase = RECOVERY_PHASE.format(phase=await deps.recovery.current_phase(project_id))
    await tracker.begin(phase)
    await deps.recovery.redrive_if_parked(project_id)
    await tracker.finish(phase)


@dataclass(frozen=True, kw_only=True)
class AutopilotDriveDependencies:
    """Collaborators of the autopilot drive."""

    stepper: AutopilotStepper
    recovery: RecoveryDependencies
    stopping: Stopping


class AutopilotDriveExecutor:
    """Step one autopilot run until the owner has to act or the run ends."""

    def __init__(self, deps: AutopilotDriveDependencies) -> None:
        self._deps = deps

    async def lock_keys(self, run: GenerationRun) -> list[str]:
        """The run itself, plus its project once it has one."""
        run_id = _autopilot_run_id(run)
        keys = [AUTOPILOT_KEY.format(run_id=run_id)]
        view = await self._deps.stepper.view(run_id)
        if view is not None and view.project_id:
            keys.append(project_key(view.project_id))
        return keys

    async def execute(self, run: GenerationRun, tracker: StepTracker) -> StepOutcome:
        """Recover an orphaned or parked phase, then step until there is nothing to do.

        Under the drive lock nothing else runs this project, so a checkpoint parked
        before a node is always left over from a dead driver: it is re-run at once
        instead of waiting out the runner's parked grace period.
        """
        run_id = _autopilot_run_id(run)
        view = await self._deps.stepper.view(run_id)
        if view is None or view.state not in DRIVEABLE_STATES:
            return StepOutcome.DONE
        if view.project_id:
            if not await recover_orphan(self._deps.recovery, run, view.project_id):
                return StepOutcome.WAIT
            await redrive_parked(self._deps.recovery, tracker, view.project_id)
        return await self._step_until_idle(run_id, tracker)

    async def _step_until_idle(self, run_id: str, tracker: StepTracker) -> StepOutcome:
        for _ in range(MAX_STEPS_PER_JOB):
            if self._deps.stopping():
                return StepOutcome.YIELD
            view = await self._deps.stepper.view(run_id)
            if view is None or view.state not in DRIVEABLE_STATES:
                return StepOutcome.DONE
            phase = view.phase or PHASE_START
            await tracker.begin(phase)
            stepped = await self._deps.stepper.step(run_id)
            await tracker.finish(phase)
            if stepped == 0:
                return StepOutcome.WAIT
        return StepOutcome.YIELD


@dataclass(frozen=True, kw_only=True)
class WorkflowResumeDependencies:
    """Collaborators of the dashboard resume."""

    resumer: WorkflowResumer
    recovery: RecoveryDependencies


class WorkflowResumeExecutor:
    """Run the dashboard resume once; on a re-pick, recover from the checkpoint.

    A re-picked resume never re-applies the review decision: its first attempt
    may already have written the feedback note or moved the checkpoint, so the
    retry only takes the orphaned row back and re-runs the parked node. When another
    dashboard resume is active for the project, that one owns it and the
    re-pick ends without touching the project.
    """

    def __init__(self, deps: WorkflowResumeDependencies) -> None:
        self._deps = deps

    @staticmethod
    async def lock_keys(run: GenerationRun) -> list[str]:
        """The project being resumed."""
        return [project_key(_resume_payload(run).project_id)]

    async def execute(self, run: GenerationRun, tracker: StepTracker) -> StepOutcome:
        """First attempt: resume. Later attempts and adoptions: reap and re-drive."""
        payload = _resume_payload(run)
        if run.last_phase is not None or payload.action == ACTION_ADOPT:
            if await recover_orphan(self._deps.recovery, run, payload.project_id):
                await redrive_parked(self._deps.recovery, tracker, payload.project_id)
            return StepOutcome.DONE
        phase = await self._deps.recovery.recovery.current_phase(payload.project_id)
        await tracker.begin(phase or PHASE_START)
        await self._deps.resumer.resume(payload)
        await tracker.finish(phase or PHASE_START)
        return StepOutcome.DONE


def _autopilot_run_id(run: GenerationRun) -> str:
    try:
        return AutopilotDrivePayload.parse(run.payload).autopilot_run_id
    except ValueError as exc:
        raise PermanentGenerationError(ERROR_BAD_PAYLOAD, str(exc)) from exc


def _resume_payload(run: GenerationRun) -> WorkflowResumePayload:
    try:
        return WorkflowResumePayload.parse(run.payload)
    except ValueError as exc:
        raise PermanentGenerationError(ERROR_BAD_PAYLOAD, str(exc)) from exc


__all__ = [
    "AutopilotDriveDependencies",
    "AutopilotDriveExecutor",
    "RecoveryDependencies",
    "WorkflowResumeDependencies",
    "WorkflowResumeExecutor",
    "project_key",
]
