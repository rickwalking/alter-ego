"""Drive the editorial facade in-process.

Creates the carousel, starts the workflow, reads the gate, and resumes
approve or revise. Provider 429/503 become a status. A lock conflict
does not call resume a second time.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_workflow import (
    ERR_REVISION_CAP_EXCEEDED,
    STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.constants.presentation_policy import (
    CREATE_TIME_PRESENTATION_POLICY_VERSION,
)
from rag_backend.infrastructure.monitoring_langfuse import propagate_attributes
from rag_backend.modules.autopilot.constants import (
    AGENT_NAME_AUTOPILOT,
    AUTOPILOT_SLIDES_CONFIG,
    CONTENT_TYPE_CAROUSEL,
    FIELD_CURRENT_PHASE,
    FIELD_IMAGE_ASSETS,
    FIELD_PHASE_STATUS,
    LANGFUSE_FIELD_AGENT_NAME,
    LANGFUSE_FIELD_CONTENT_TYPE,
    LANGFUSE_FIELD_PHASE,
    LANGFUSE_FIELD_PROJECT_ID,
    LANGUAGE_PT_BR,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    REVIEWER_UNSET,
    SOURCE_FIELD_TITLE,
    SOURCE_FIELD_TYPE,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateSnapshot,
    ImageFact,
    ProjectSpec,
    ResumeCommand,
    ResumeResult,
    ResumeStatus,
    SnapshotParts,
    StartCommand,
    StartStatus,
)
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.snapshot import assemble_snapshot
from rag_backend.modules.autopilot.infrastructure.jpeg_size import jpeg_size
from rag_backend.modules.editorial.public import (
    AclOptimisticLockingAdapter,
    AutomationResume,
    AutomationStart,
    CarouselAutomationAcl,
    CarouselProject,
    CarouselProjectWriteOwner,
    EditorialPorts,
    EditorialService,
    EditorialWorkflowEngine,
    EditorialWorkflowHandlers,
    EngineReviewDecisionAdapter,
    LegacyCarouselAcl,
    ResearchSourceType,
    StartWorkflowCommand,
    WorkflowEngine,
    WorkflowStateView,
    build_resume_input,
    build_start_input,
    content_approve_blocker,
    is_provider_outage,
)

EngineFactory = Callable[[], EditorialWorkflowEngine]
_CONTENT = "content"


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
        """Insert a private pt-BR carousel owned by the autopilot user."""
        project = CarouselProject(
            topic=spec.topic,
            audience=spec.audience,
            niche=spec.niche,
            slides_config=AUTOPILOT_SLIDES_CONFIG,
            language=LANGUAGE_PT_BR,
            generate_images=True,
            owner_id=spec.owner_user_id or None,
            presentation_policy_version=CREATE_TIME_PRESENTATION_POLICY_VERSION,
        )
        return await self._acl.create_project(project)

    async def start(self, command: StartCommand) -> StartStatus:
        """Start the workflow under autopilot Langfuse metadata."""
        engine = self._config.engine_factory()
        workflow = StartWorkflowCommand(
            project_id=command.project_id,
            workflow_input=build_start_input(_start_input(command.spec)),
        )
        metadata = _trace(command.project_id, command.phase)
        try:
            with propagate_attributes(metadata=metadata):
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
        """Load workflow state and measure image files. No resume."""
        engine = self._config.engine_factory()
        view = await _handlers(self._config.session).get_state(
            _as_engine(engine),
            project_id,
        )
        state = _state_of(view)
        lock_version = view.lock_version if view is not None else 1
        return assemble_snapshot(
            SnapshotParts(
                state=state,
                images=_images(state.get(FIELD_IMAGE_ASSETS)),
                slides_total=await self._slides_total(project_id),
                lock_version=lock_version,
                stale=await self._is_stale(project_id),
                engine_blocker=content_approve_blocker(state) or "",
            )
        )

    async def resume(self, command: ResumeCommand) -> ResumeResult:
        """Bump the lock, then resume once. A conflict skips the resume."""
        engine = self._config.engine_factory()
        service = _service(self._config.session, self._acl, engine)
        metadata = _trace(command.project_id, command.phase)
        try:
            with propagate_attributes(metadata=metadata):
                await service.bump_resume_lock_version(
                    command.project_id,
                    command.expected_version,
                )
                await service.record_review_decision(
                    _resume_input(command, self._config.session)
                )
        except Exception as exc:
            status = _resume_status(exc)
            if status is None:
                raise
            if status is ResumeStatus.PROVIDER_OUTAGE:
                await self._config.session.rollback()
            return ResumeResult(status=status)
        return ResumeResult(status=ResumeStatus.APPLIED)

    async def _slides_total(self, project_id: str) -> int:
        return await self._acl.slide_total(project_id)

    async def _is_stale(self, project_id: str) -> bool:
        beat = await self._acl.heartbeat(project_id)
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


def _service(
    session: AsyncSession,
    acl: CarouselAutomationAcl,
    engine: EditorialWorkflowEngine,
) -> EditorialService:
    ports = EditorialPorts(
        optimistic_locking=AclOptimisticLockingAdapter(_acl(session)),
        review_decision=EngineReviewDecisionAdapter(engine),
    )
    return EditorialService(acl.repository, ports)


def _start_input(spec: ProjectSpec) -> AutomationStart:
    return AutomationStart(
        topic=spec.topic,
        audience=spec.audience,
        brief=spec.brief,
        sources=_source_rows(spec.sources),
        user_id=spec.owner_user_id,
    )


def _source_rows(sources: tuple[str, ...]) -> tuple[dict[str, str], ...]:
    kind = ResearchSourceType.DOCUMENTATION.value
    return tuple(_source_row(url, kind) for url in sources)


def _source_row(url: str, kind: str) -> dict[str, str]:
    return {
        SOURCE_FIELD_TITLE: url,
        _CONTENT: url,
        SOURCE_FIELD_TYPE: kind,
    }


def _state_of(view: WorkflowStateView | None) -> dict[str, object]:
    if view is None:
        return {
            FIELD_CURRENT_PHASE: "",
            FIELD_PHASE_STATUS: PHASE_STATUS_FAILED,
        }
    return {str(key): value for key, value in view.state.items()}


def _resume_input(command: ResumeCommand, session: AsyncSession) -> object:
    return build_resume_input(
        AutomationResume(
            project_id=command.project_id,
            action=command.action,
            reviewer_id=REVIEWER_UNSET,
            feedback=command.feedback,
            structured_feedback=_structured_feedback(command),
            session=session,
        )
    )


def _structured_feedback(command: ResumeCommand) -> dict[str, object] | None:
    if not command.target_phase:
        return None
    return {STRUCTURED_FEEDBACK_TARGET_PHASE_KEY: command.target_phase}


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


def _trace(project_id: str, phase: str) -> dict[str, str]:
    return {
        LANGFUSE_FIELD_CONTENT_TYPE: CONTENT_TYPE_CAROUSEL,
        LANGFUSE_FIELD_AGENT_NAME: AGENT_NAME_AUTOPILOT,
        LANGFUSE_FIELD_PHASE: phase,
        LANGFUSE_FIELD_PROJECT_ID: project_id,
    }


def _start_status(exc: BaseException) -> StartStatus | None:
    if not is_provider_outage(exc):
        return None
    return StartStatus.PROVIDER_OUTAGE


def _resume_status(exc: BaseException) -> ResumeStatus | None:
    if is_provider_outage(exc):
        return ResumeStatus.PROVIDER_OUTAGE
    if not isinstance(exc, ValueError):
        return None
    if str(exc) == ERR_VERSION_CONFLICT:
        return ResumeStatus.VERSION_CONFLICT
    if str(exc) == ERR_REVISION_CAP_EXCEEDED:
        return ResumeStatus.REVISION_CAP
    return None


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
