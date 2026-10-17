"""Drive the editorial facade in-process.

Creates the carousel, starts the workflow, reads the gate, and resumes
approve or revise. Provider 429/503 become a status. A lock conflict
does not call resume a second time.

AE-0363: approve, revise, and re-drive run through the editorial
``run_automation_phase`` facade operation, the same run-owned path as the
HTTP resume. The tick commits the lock bump and the ``in_progress`` flip
before the phase runs, so no transaction is held across LLM work, and the
row carries ``run_started_at`` and a live heartbeat while the phase runs.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants import IMAGE_MODEL_OPENAI
from rag_backend.domain.constants.carousel import CAROUSEL_DEFAULT_SLIDES_CONFIG
from rag_backend.domain.constants.carousel_cta import DEFAULT_CTA_GOAL
from rag_backend.domain.constants.carousel_workflow import (
    ERR_NOTHING_TO_REDRIVE,
    ERR_RESUME_ALREADY_IN_PROGRESS,
    ERR_REVISION_CAP_EXCEEDED,
    STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
)
from rag_backend.domain.constants.content_feedback import (
    FEEDBACK_SOURCE_AUTOPILOT,
    STRUCTURED_FEEDBACK_SOURCE_KEY,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.infrastructure.monitoring_langfuse import (
    WorkflowTraceScope,
    workflow_trace_scope,
)
from rag_backend.modules.autopilot.constants import (
    AGENT_NAME_AUTOPILOT,
    CONTENT_TYPE_CAROUSEL,
    FIELD_CURRENT_PHASE,
    FIELD_IMAGE_ASSETS,
    FIELD_PHASE_STATUS,
    LANGUAGE_PT_BR,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    REVIEWER_UNSET,
)
from rag_backend.modules.autopilot.domain.carousel_defaults import rotated_theme
from rag_backend.modules.autopilot.domain.gate import (
    GateSnapshot,
    ImageFact,
    ProjectSpec,
    RedriveCommand,
    ResumeCommand,
    ResumeResult,
    ResumeStatus,
    SnapshotParts,
    StartCommand,
    StartStatus,
)
from rag_backend.modules.autopilot.domain.parked import (
    GateStatus,
    GateStatusInput,
    RowRun,
    reconcile_gate_status,
)
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.snapshot import assemble_snapshot
from rag_backend.modules.autopilot.infrastructure.jpeg_size import jpeg_size
from rag_backend.modules.autopilot.infrastructure.pov_project import (
    policy_version_for,
    pov_fields_for,
    start_input_for,
)
from rag_backend.modules.autopilot.infrastructure.quote_gate import quote_violations
from rag_backend.modules.autopilot.parked_constants import PARKED_GRACE_SECONDS
from rag_backend.modules.editorial.public import (
    AutomationRun,
    CarouselAutomationAcl,
    CarouselProject,
    CarouselProjectWriteOwner,
    EditorialWorkflowEngine,
    EditorialWorkflowHandlers,
    LegacyCarouselAcl,
    RunHeartbeat,
    StartWorkflowCommand,
    WorkflowEngine,
    WorkflowStateView,
    content_approve_blocker,
    is_provider_outage,
    redrive_automation_phase,
    run_automation_phase,
)

EngineFactory = Callable[[], EditorialWorkflowEngine]


@dataclass(frozen=True, kw_only=True)
class EditorialDriverConfig:
    """Session-scoped collaborators for one worker tick."""

    session: AsyncSession
    engine_factory: EngineFactory
    clock: Clock
    stale_after_seconds: int


class InProcessEditorialDriver:
    """EditorialDriver backed by the editorial public facade."""

    def __init__(self, config: EditorialDriverConfig) -> None:
        self._config = config
        self._acl = CarouselAutomationAcl(config.session)

    async def create_project(self, spec: ProjectSpec) -> str:
        """Insert a private pt-BR carousel owned by the autopilot user.

        AE-0361: OpenAI images, the scout's preset, and its
        image guidance (or the template) as the project's visual direction.
        AE-0362: the pipeline's default 7-slide config, the count the editorial
        pipeline actually builds.
        AE-0377: a POV spec creates a "Ponto de Vista" carousel from the
        owner-confirmed thesis (pov_hook_v1, follow CTA). PR #106 review: with
        the scout's format and slide count, the slide-1 photo (staged by the
        editorial ACL) and the autopilot persona.
        AE-0395: the palette rotates per São Paulo day (``rotated_theme``).
        """
        project = CarouselProject(
            topic=spec.topic,
            audience=spec.audience,
            niche=spec.niche,
            slides_config=CAROUSEL_DEFAULT_SLIDES_CONFIG,
            language=LANGUAGE_PT_BR,
            generate_images=True,
            image_model=IMAGE_MODEL_OPENAI,
            image_style=spec.image_style,
            theme=rotated_theme(self._config.clock.now()),
            custom_visual_details=spec.image_guidance or None,
            owner_id=spec.owner_user_id or None,
            presentation_policy_version=policy_version_for(spec),
            content_mode=spec.content_mode,
            cta_goal=DEFAULT_CTA_GOAL,
            slide_cover=spec.cover,
            **pov_fields_for(spec),
        )
        return await self._acl.create_project(project)

    async def start(self, command: StartCommand) -> StartStatus:
        """Start the workflow; its phase traces carry the autopilot agent."""
        engine = self._config.engine_factory()
        workflow = StartWorkflowCommand(
            project_id=command.project_id,
            workflow_input=await self._acl.start_input(start_input_for(command.spec)),
        )
        try:
            with workflow_trace_scope(_trace_scope(command.project_id)):
                handlers = _handlers(self._config.session)
                await handlers.start(_as_engine(engine), workflow)
        except Exception as exc:
            status = _start_status(exc)
            if status is None:
                raise
            await self._config.session.rollback()
            return status
        return StartStatus.STARTED

    async def read_gate(self, project_id: str) -> GateSnapshot:
        """Load workflow state and measure image files. No resume.

        AE-0363: the status comes from the checkpoint reconciled with the row,
        so a run in flight waits and a parked workflow is flagged.
        """
        engine = self._config.engine_factory()
        view = await _handlers(self._config.session).get_state(
            _as_engine(engine),
            project_id,
        )
        state = _state_of(view)
        lock_version = view.lock_version if view is not None else 1
        beat = await self._acl.heartbeat(project_id)
        gate = self._gate_status(state, beat)
        state[FIELD_PHASE_STATUS] = gate.phase_status
        return assemble_snapshot(
            SnapshotParts(
                state=state,
                images=_images(state.get(FIELD_IMAGE_ASSETS)),
                slides_total=await self._slides_total(project_id),
                lock_version=lock_version,
                stale=self._is_stale(beat),
                engine_blocker=content_approve_blocker(state) or "",
                parked=gate.parked,
                parked_overdue=gate.parked_overdue,
                hero_images_total=await self._acl.hero_image_total(project_id),
                pov=await self._acl.is_pov(project_id),
                quote_violations=await quote_violations(self._acl, project_id, state),
            )
        )

    async def resume(self, command: ResumeCommand) -> ResumeResult:
        """Approve or revise once through the run-owned editorial path."""
        return await self._run(
            run_automation_phase,
            AutomationRun(
                engine=self._config.engine_factory(),
                session=self._config.session,
                project_id=command.project_id,
                expected_version=command.expected_version,
                action=command.action,
                reviewer_id=REVIEWER_UNSET,
                feedback=command.feedback,
                structured_feedback=_structured_feedback(command),
            ),
        )

    async def redrive(self, command: RedriveCommand) -> ResumeResult:
        """Re-run a parked pending node once (AE-0363). No review is sent."""
        return await self._run(
            redrive_automation_phase,
            AutomationRun(
                engine=self._config.engine_factory(),
                session=self._config.session,
                project_id=command.project_id,
                expected_version=command.expected_version,
                action="",
            ),
        )

    async def _run(
        self,
        operation: Callable[[AutomationRun], Awaitable[None]],
        run: AutomationRun,
    ) -> ResumeResult:
        """Run one facade operation; map the refusals it raises to a status.

        Refusals are raised before the run start is committed, so the tick
        transaction holds nothing of the run. A failure inside the phase is not
        raised: the run wrapper marked the row ``failed`` and the next read
        escalates it.
        """
        try:
            with workflow_trace_scope(_trace_scope(run.project_id)):
                await operation(run)
        except Exception as exc:
            status = _resume_status(exc)
            if status is None:
                raise
            if status is ResumeStatus.PROVIDER_OUTAGE:
                await self._config.session.rollback()
            return ResumeResult(status=status)
        return ResumeResult(status=ResumeStatus.APPLIED)

    def _gate_status(
        self, state: dict[str, object], beat: RunHeartbeat | None
    ) -> GateStatus:
        return reconcile_gate_status(
            GateStatusInput(
                engine_phase=str(state.get(FIELD_CURRENT_PHASE, "")),
                engine_status=str(state.get(FIELD_PHASE_STATUS, "")),
                row=self._row_run(beat),
                grace_seconds=PARKED_GRACE_SECONDS,
            )
        )

    def _row_run(self, beat: RunHeartbeat | None) -> RowRun | None:
        if beat is None:
            return None
        idle: float | None = None
        if beat.updated_at is not None:
            elapsed = self._config.clock.now() - _aware(beat.updated_at)
            idle = elapsed.total_seconds()
        return RowRun(phase_status=beat.phase_status, idle_seconds=idle)

    async def _slides_total(self, project_id: str) -> int:
        return await self._acl.slide_total(project_id)

    def _is_stale(self, beat: RunHeartbeat | None) -> bool:
        if beat is None or beat.heartbeat_at is None:
            return False
        if beat.phase_status != PHASE_STATUS_IN_PROGRESS:
            return False
        heartbeat = _aware(beat.heartbeat_at)
        limit = timedelta(seconds=self._config.stale_after_seconds)
        return self._config.clock.now() - heartbeat > limit


def _as_engine(engine: EditorialWorkflowEngine) -> WorkflowEngine:
    """The service is the engine. The protocol types ``db`` as object."""
    return cast(WorkflowEngine, engine)


def _handlers(session: AsyncSession) -> EditorialWorkflowHandlers:
    return EditorialWorkflowHandlers(_acl(session))


def _acl(session: AsyncSession) -> LegacyCarouselAcl:
    return LegacyCarouselAcl(session, CarouselProjectWriteOwner(session))


def _state_of(view: WorkflowStateView | None) -> dict[str, object]:
    if view is None:
        return {
            FIELD_CURRENT_PHASE: "",
            FIELD_PHASE_STATUS: PHASE_STATUS_FAILED,
        }
    return {str(key): value for key, value in view.state.items()}


def _structured_feedback(command: ResumeCommand) -> dict[str, object] | None:
    structured: dict[str, object] = {}
    if command.target_phase:
        structured[STRUCTURED_FEEDBACK_TARGET_PHASE_KEY] = command.target_phase
    if command.feedback.strip():
        # AE-0405: tag gate feedback so it is applied once, never re-fed.
        structured[STRUCTURED_FEEDBACK_SOURCE_KEY] = FEEDBACK_SOURCE_AUTOPILOT
    return structured or None


def _images(raw: object) -> tuple[ImageFact, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(_measure(str(path)) for path in raw if isinstance(path, str))


def _measure(path: str) -> ImageFact:
    file = Path(path)
    if not file.is_file():
        return ImageFact(present=False, is_jpeg=False, width=0, height=0)
    size = jpeg_size(file.read_bytes())
    if size is None:
        return ImageFact(present=True, is_jpeg=False, width=0, height=0)
    return ImageFact(present=True, is_jpeg=True, width=size.width, height=size.height)


def _trace_scope(project_id: str) -> WorkflowTraceScope:
    """AE-0390: the phase seams name the trace; the run adds the owner."""
    return WorkflowTraceScope(
        project_id=project_id,
        agent_name=AGENT_NAME_AUTOPILOT,
        content_type=CONTENT_TYPE_CAROUSEL,
    )


def _start_status(exc: BaseException) -> StartStatus | None:
    if not is_provider_outage(exc):
        return None
    return StartStatus.PROVIDER_OUTAGE


def _resume_status(exc: BaseException) -> ResumeStatus | None:
    if is_provider_outage(exc):
        return ResumeStatus.PROVIDER_OUTAGE
    if not isinstance(exc, ValueError):
        return None
    return _REFUSALS.get(str(exc))


_REFUSALS: dict[str, ResumeStatus] = {
    ERR_VERSION_CONFLICT: ResumeStatus.VERSION_CONFLICT,
    ERR_REVISION_CAP_EXCEEDED: ResumeStatus.REVISION_CAP,
    ERR_RESUME_ALREADY_IN_PROGRESS: ResumeStatus.IN_PROGRESS,
    ERR_NOTHING_TO_REDRIVE: ResumeStatus.NOT_PARKED,
}


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
