"""Drive one autopilot run one step per tick.

The session is already bound on the injected ports. ``tick`` takes no
database argument so this module stays free of SQLAlchemy. The worker
adapter in ``bootstrap`` opens the session and calls ``tick``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import structlog

from rag_backend.modules.autopilot.application.feedback import (
    ReviseFeedbackRequest,
    revise_feedback,
)
from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.application.rework_step import (
    ReworkDependencies,
    ReworkStep,
)
from rag_backend.modules.autopilot.application.run_recovery import (
    RecoveryDependencies,
    RunRecovery,
)
from rag_backend.modules.autopilot.constants import (
    GATE_FINAL_REVIEW,
    GATE_RESEARCH,
    LOG_RUNNER,
    MAX_START_ATTEMPTS,
    REASON_GENERATING,
    REASON_OWNER_UNCONFIGURED,
    REASON_PERSONA_SCORE,
    REASON_PROJECT_MISSING,
    REASON_READY,
    REASON_RESEARCH,
    REASON_REVISION_CAP,
    REASON_START_FAILED,
    REASON_TOPIC_MISSING,
    RUNS_PER_TICK,
)
from rag_backend.modules.autopilot.domain.carousel_defaults import (
    GuidanceRequest,
    image_guidance_for,
)
from rag_backend.modules.autopilot.domain.gate import (
    AttachProjectCommand,
    EditorialDriver,
    GateAction,
    GateSnapshot,
    OwnerReadyNotice,
    OwnerReadyNotifier,
    PolicyDecision,
    ProjectSpec,
    RedriveCommand,
    ResumeCommand,
    ResumeStatus,
    StartAttemptCommand,
    StartCommand,
    StartStatus,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.policy import decide, source_has_content
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    Clock,
    TopicCandidateRepository,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.recovery import RunRecoveryStore
from rag_backend.modules.autopilot.notify_constants import (
    REASON_NOTIFIER_UNCONFIGURED,
)
from rag_backend.modules.autopilot.parked_constants import (
    LOG_RUNNER_REDRIVE,
    REASON_ENGINE_PARKED,
)
from rag_backend.modules.editorial.public import (
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
)

logger = structlog.get_logger()

_ACTIVE: tuple[AutopilotRunState, ...] = (
    AutopilotRunState.GENERATING,
    AutopilotRunState.REWORKING,
    AutopilotRunState.QUEUED,
)


@dataclass(frozen=True, kw_only=True)
class RunnerDependencies:
    """Ports for one session. The worker builds a new bundle each tick."""

    runs: AutopilotRunRepository
    topics: TopicCandidateRepository
    editorial: EditorialDriver
    notices: OwnerReadyNotifier
    recovery: RunRecoveryStore
    owner_user_id: str
    notifier_configured: bool = True
    clock: Clock = field(default_factory=SystemClock)


@dataclass(frozen=True, kw_only=True)
class _Step:
    run: AutopilotRun
    snapshot: GateSnapshot
    decision: PolicyDecision


class AutopilotRunner:
    """Advance at most one run: start, one gate, or hand off to the owner."""

    def __init__(self, deps: RunnerDependencies) -> None:
        self._deps = deps
        self._recovery = RunRecovery(_recovery_deps(deps))
        self._rework = ReworkStep(
            ReworkDependencies(
                runs=deps.runs,
                editorial=deps.editorial,
                recovery=deps.recovery,
                escalations=self._recovery,
            )
        )

    async def tick(self) -> int:
        """Sweep expiries and fixed escalations, then step at most one run.

        An engine error the driver did not classify ends that run with a
        reason; it never propagates and rolls back the worker tick.
        """
        swept = await self._recovery.sweep()
        run = await _first_run(self._deps.runs)
        if run is None:
            return swept
        try:
            stepped = await self._step(run)
        except Exception as exc:
            stepped = await self._recovery.contain(run, exc)
        return swept + stepped

    async def _step(self, run: AutopilotRun) -> int:
        if run.state is AutopilotRunState.QUEUED:
            return await self._tick_queued(run)
        reworked = await self._rework.try_apply(run)
        if reworked is not None:
            return reworked
        return await self._tick_active(run)

    async def _tick_queued(self, run: AutopilotRun) -> int:
        if not self._deps.owner_user_id.strip():
            await self._move(run, AutopilotRunState.FAILED, REASON_OWNER_UNCONFIGURED)
            return 1
        spec = await self._spec(run)
        if spec is None:
            await self._move(run, AutopilotRunState.FAILED, REASON_TOPIC_MISSING)
            return 1
        project_id = await self._project_id(run, spec)
        if project_id is None:
            return 0
        return await self._start(run, spec, project_id)

    async def _tick_active(self, run: AutopilotRun) -> int:
        project_id = run.carousel_project_id
        if project_id is None:
            await self._move(run, AutopilotRunState.FAILED, REASON_PROJECT_MISSING)
            return 1
        snapshot = await self._deps.editorial.read_gate(project_id)
        decision = decide(snapshot)
        return await self._apply(_Step(run=run, snapshot=snapshot, decision=decision))

    async def _start(
        self,
        run: AutopilotRun,
        spec: ProjectSpec,
        project_id: str,
    ) -> int:
        command = StartCommand(project_id=project_id, spec=spec, phase=GATE_RESEARCH)
        status = await self._deps.editorial.start(command)
        if status is StartStatus.PROVIDER_OUTAGE:
            await self._count_start_failure(run)
            return 1
        await self._move(run, AutopilotRunState.GENERATING, REASON_GENERATING)
        return 1

    async def _apply(self, step: _Step) -> int:
        handlers: dict[GateAction, Callable[[_Step], Awaitable[int]]] = {
            GateAction.WAIT: self._wait,
            GateAction.STOP: self._stop,
            GateAction.ESCALATE: self._escalate,
            GateAction.REVISE: self._revise,
            GateAction.APPROVE: self._approve,
            GateAction.REDRIVE: self._redrive,
        }
        return await handlers[step.decision.action](step)

    async def _wait(self, step: _Step) -> int:
        logger.info(
            LOG_RUNNER,
            run_id=str(step.run.run_id),
            action=GateAction.WAIT.value,
            owner_set=bool(self._deps.owner_user_id.strip()),
        )
        return 0

    async def _stop(self, step: _Step) -> int:
        if not self._deps.notifier_configured:
            await self._escalate_at(step, REASON_NOTIFIER_UNCONFIGURED)
            return 1
        moved = await self._move(
            step.run,
            AutopilotRunState.AWAITING_OWNER,
            REASON_READY,
        )
        project_id = step.run.carousel_project_id
        if moved and project_id is not None:
            await self._deps.notices.notify_ready(_ready_notice(step, project_id))
        return 1

    async def _escalate(self, step: _Step) -> int:
        await self._escalate_at(step, step.decision.reason)
        return 1

    async def _escalate_at(self, step: _Step, reason: str) -> None:
        if await self._move(step.run, AutopilotRunState.ESCALATED, reason):
            await self._recovery.mark(step.run, step.snapshot.lock_version)

    async def _revise(self, step: _Step) -> int:
        if step.snapshot.phase == GATE_FINAL_REVIEW:
            return await self._stop(step)
        feedback = revise_feedback(_feedback_request(step))
        return await self._resume(step, REVIEW_ACTION_REVISE, feedback)

    async def _approve(self, step: _Step) -> int:
        if step.snapshot.phase == GATE_FINAL_REVIEW:
            return await self._stop(step)
        return await self._resume(step, REVIEW_ACTION_APPROVE, "")

    async def _resume(self, step: _Step, action: str, feedback: str) -> int:
        project_id = step.run.carousel_project_id or ""
        result = await self._deps.editorial.resume(
            ResumeCommand(
                project_id=project_id,
                action=action,
                expected_version=step.snapshot.lock_version,
                feedback=feedback,
                phase=step.snapshot.phase,
            )
        )
        if result.status is ResumeStatus.REVISION_CAP:
            await self._escalate_at(step, REASON_REVISION_CAP)
        return 1

    async def _redrive(self, step: _Step) -> int:
        """Re-run a parked phase once; escalate when nothing is parked (AE-0363).

        A re-drive that fails marks the carousel ``failed``, and the next
        tick escalates it, so a parked workflow is never retried silently.
        """
        project_id = step.run.carousel_project_id or ""
        logger.warning(
            LOG_RUNNER_REDRIVE,
            run_id=str(step.run.run_id),
            project_id=project_id,
            phase=step.snapshot.phase,
            phase_status=step.snapshot.phase_status,
        )
        result = await self._deps.editorial.redrive(
            RedriveCommand(
                project_id=project_id,
                expected_version=step.snapshot.lock_version,
                phase=step.snapshot.phase,
            )
        )
        if result.status is ResumeStatus.NOT_PARKED:
            await self._escalate_at(step, REASON_ENGINE_PARKED)
        return 1

    async def _spec(self, run: AutopilotRun) -> ProjectSpec | None:
        topic = await self._deps.topics.get_topic(run.topic_candidate_id)
        if topic is None:
            return None
        return ProjectSpec(
            topic=topic.title,
            audience=topic.audience,
            niche=topic.niche,
            brief=topic.brief,
            sources=topic.sources,
            owner_user_id=self._deps.owner_user_id,
            image_style=topic.image_style,
            image_guidance=image_guidance_for(_guidance_request(topic)),
        )

    async def _project_id(self, run: AutopilotRun, spec: ProjectSpec) -> str | None:
        if run.carousel_project_id is not None:
            return run.carousel_project_id
        project_id = await self._deps.editorial.create_project(spec)
        attached = await self._deps.runs.attach_project(
            AttachProjectCommand(run_id=run.run_id, project_id=project_id)
        )
        if not attached:
            return None
        return project_id

    async def _count_start_failure(self, run: AutopilotRun) -> None:
        attempts = run.start_attempts + 1
        await self._deps.runs.note_start_attempt(
            StartAttemptCommand(
                run_id=run.run_id,
                attempts=attempts,
                reason=REASON_START_FAILED,
            )
        )
        if attempts >= MAX_START_ATTEMPTS:
            await self._move(run, AutopilotRunState.FAILED, REASON_START_FAILED)

    async def _move(
        self,
        run: AutopilotRun,
        new: AutopilotRunState,
        reason: str,
    ) -> bool:
        return await self._deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=run.state,
                new=new,
                reason=reason,
            )
        )


def _recovery_deps(deps: RunnerDependencies) -> RecoveryDependencies:
    return RecoveryDependencies(
        runs=deps.runs,
        editorial=deps.editorial,
        notices=deps.notices,
        recovery=deps.recovery,
        clock=deps.clock,
        notifier_configured=deps.notifier_configured,
    )


async def _first_run(runs: AutopilotRunRepository) -> AutopilotRun | None:
    for state in _ACTIVE:
        query = RunListQuery(state=state, limit=RUNS_PER_TICK)
        found = await runs.list_by_state(query)
        if found:
            return found[0]
    return None


def _ready_notice(step: _Step, project_id: str) -> OwnerReadyNotice:
    return OwnerReadyNotice(
        run_id=step.run.run_id,
        project_id=project_id,
        revision=step.snapshot.lock_version,
        persona_score=step.snapshot.persona_score,
        sources_count=len(step.snapshot.sources),
    )


def _feedback_request(step: _Step) -> ReviseFeedbackRequest:
    return ReviseFeedbackRequest(
        phase=step.snapshot.phase,
        reason=step.decision.reason,
        detail=_detail(step.snapshot, step.decision.reason),
    )


def _detail(snapshot: GateSnapshot, reason: str) -> str:
    if reason == REASON_PERSONA_SCORE and snapshot.persona_score is not None:
        return str(snapshot.persona_score)
    if reason == REASON_RESEARCH:
        usable = sum(1 for source in snapshot.sources if source_has_content(source))
        return str(usable)
    return ""


def _guidance_request(topic: TopicCandidate) -> GuidanceRequest:
    return GuidanceRequest(
        image_style=topic.image_style,
        niche=topic.niche,
        image_guidance=topic.image_guidance,
    )
