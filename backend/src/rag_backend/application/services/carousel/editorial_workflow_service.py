"""Editorial carousel workflow orchestration (AI-004 + Phase 3 WF-*)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.carousel_editorial_orchestrator import (
    CarouselEditorialOrchestrator,
)
from rag_backend.application.services.carousel.editorial_workflow_events import (
    PhaseEventEmitContext,
    ReviewEventEmitRequest,
    emit_phase_event,
    emit_review_event,
)
from rag_backend.application.services.carousel.editorial_workflow_service_helpers import (
    FeedbackCorrectionContext,
    ResumeContext,
    RevisionCapValidationContext,
    prepare_resume_workflow,
    record_feedback_correction,
    stream_workflow_phase_updates,
    validate_revision_cap,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
    ResumeWorkflowInput,
    ReviewEventEmitContext,
    publish_workflow_sse_updates,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    read_checkpoint_phase as read_engine_checkpoint_phase,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.application.services.notification_service import NotificationService
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_IMAGES,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REJECT,
    REVIEW_ACTION_REVISE,
    STRUCTURED_FEEDBACK_KEY,
    WORKFLOW_METADATA_EDITORIAL_7_PHASE,
    WORKFLOW_STATE_LINKEDIN_POST_EN_KEY,
    WORKFLOW_STATE_LINKEDIN_POST_PT_KEY,
    WORKFLOW_TRACE_PHASE_HUMAN_REVIEW,
    WORKFLOW_TRACE_PHASE_REVIEW,
)
from rag_backend.domain.constants.workflow_validation import CONTENT_TYPE_CAROUSEL
from rag_backend.domain.models import CarouselStatus
from rag_backend.domain.models.carousels import ReviewEventParams
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.monitoring_langfuse import (
    _TraceConfig,
    create_workflow_trace,
    propagate_attributes,
    record_human_review,
)


@dataclass
class EditorialWorkflowConfig:
    """Configuration bundle for EditorialWorkflowService."""

    llm: BaseChatModel
    checkpointer: object | None = None
    event_service: WorkflowEventService | None = None
    notification_service: NotificationService | None = None
    image_registry: ImageProviderRegistry | None = None


class EditorialWorkflowService:
    """Coordinates AI agents, LangGraph workflow, events, and Langfuse tracing."""

    def __init__(
        self,
        config: EditorialWorkflowConfig,
    ) -> None:
        self._llm = config.llm
        self._orchestrator = CarouselEditorialOrchestrator(
            llm=config.llm,
            checkpointer=config.checkpointer,
            image_registry=config.image_registry,
        )
        self._events = config.event_service
        self._notifications = config.notification_service or NotificationService()

    async def start_workflow(
        self,
        project_id: str,
        workflow_input: EditorialWorkflowStartInput,
        db: AsyncSession | None = None,
    ) -> CarouselWorkflowState:
        """Run research synthesis then pause at the first human review gate."""
        existing = await self._orchestrator.get_state(project_id)
        if existing is not None and str(existing.get("current_phase", "")).strip():
            return existing

        _trace = create_workflow_trace(
            config=_TraceConfig(
                project_id=UUID(project_id),
                user_id=workflow_input.user_id,
                content_type=CONTENT_TYPE_CAROUSEL,
                metadata={"workflow": WORKFLOW_METADATA_EDITORIAL_7_PHASE},
            ),
        )

        with propagate_attributes(
            metadata={"project_id": project_id, "phase": PHASE_RESEARCH},
        ):
            research_findings = await self._orchestrator.synthesize_research(
                workflow_input.sources,
            )

        initial_brief = {
            "topic": workflow_input.topic,
            "audience": workflow_input.audience,
            "brief": workflow_input.brief,
            "sources": workflow_input.sources,
        }
        state = await self._orchestrator.start(
            project_id,
            initial_brief,
            research_findings=research_findings,
        )
        persisted = await self._orchestrator.get_state(project_id)
        if persisted is not None:
            state = persisted
        if workflow_input.reviewer_id:
            await self._orchestrator.update_state(
                project_id,
                {"assigned_reviewer_id": workflow_input.reviewer_id},
            )
            if db is not None:
                project = await db.get(CarouselProjectModel, project_id)
                if project is not None:
                    project.assigned_reviewer_id = workflow_input.reviewer_id
            assigned_state = await self._orchestrator.get_state(project_id)
            if assigned_state is not None:
                state = assigned_state
        await self._sync_project_phase(db, project_id, state)
        await emit_phase_event(
            db=db,
            event_service=self._events,
            ctx=PhaseEventEmitContext(
                project_id=project_id,
                state=state,
                user_id=workflow_input.user_id,
            ),
        )
        if db and workflow_input.reviewer_id:
            await self._notifications.create_review_request(
                db,
                user_id=workflow_input.reviewer_id,
                content_id=project_id,
                content_type=CONTENT_TYPE_CAROUSEL,
                title=workflow_input.topic,
            )
        await publish_workflow_sse_updates(project_id, state)
        return state

    async def read_checkpoint_phase(self, project_id: str) -> str:
        """Return checkpoint phase for structured feedback validation."""
        return await read_engine_checkpoint_phase(
            self._orchestrator.engine,
            project_id,
        )

    async def _sync_project_phase(
        self,
        db: AsyncSession | None,
        project_id: str,
        state: CarouselWorkflowState,
    ) -> None:
        """Keep carousel project row in sync with workflow state for the Kanban board."""
        if db is None:
            return
        project = await db.get(CarouselProjectModel, project_id)
        if project is None:
            return
        project.current_phase = str(state.get("current_phase", project.current_phase))
        project.phase_status = str(state.get("phase_status", project.phase_status))
        if str(state.get("phase_status", "")) == PHASE_STATUS_FAILED:
            project.status = CarouselStatus.FAILED.value
        raw_workflow_status = state.get("workflow_status")
        if raw_workflow_status is not None:
            project.workflow_status = str(raw_workflow_status)
        for attr, key in [
            ("caption", "caption"),
            ("blog_markdown", "blog_markdown"),
            ("linkedin_post_pt", WORKFLOW_STATE_LINKEDIN_POST_PT_KEY),
            ("linkedin_post_en", WORKFLOW_STATE_LINKEDIN_POST_EN_KEY),
        ]:
            val = state.get(key)
            if isinstance(val, str) and val.strip():
                setattr(project, attr, val)
        await db.flush()

    async def resume_workflow(
        self,
        params: ResumeWorkflowInput,
    ) -> CarouselWorkflowState:
        """Resume workflow after human review."""
        prior = await self._orchestrator.get_state(params.project_id)
        if params.action == REVIEW_ACTION_REVISE and prior is not None:
            await validate_revision_cap(
                prior,
                RevisionCapValidationContext(
                    project_id=params.project_id,
                    project_title=params.project_title,
                    db=params.db,
                    notifications=self._notifications,
                ),
            )
        await prepare_resume_workflow(
            ResumeContext(
                orchestrator=self._orchestrator,
                project_id=params.project_id,
                action=params.action,
                prior=prior,
                feedback=params.feedback,
            ),
        )
        trace = create_workflow_trace(
            config=_TraceConfig(
                project_id=UUID(params.project_id),
                user_id=params.reviewer_id,
                content_type=CONTENT_TYPE_CAROUSEL,
                metadata={"phase": WORKFLOW_TRACE_PHASE_HUMAN_REVIEW},
            ),
        )
        if trace is not None:
            record_human_review(
                trace=trace,
                params=ReviewEventParams(
                    phase=WORKFLOW_TRACE_PHASE_REVIEW,
                    action=params.action,
                    reviewer_id=params.reviewer_id,
                    time_to_respond=None,
                    feedback=params.feedback,
                ),
            )
        workflow_input = EditorialWorkflowStartInput(
            topic="",
            audience="",
            brief="",
            sources=[],
            persona=params.persona,
            user_id=params.reviewer_id,
        )
        graph_action = (
            REVIEW_ACTION_REJECT
            if params.action in {REVIEW_ACTION_REVISE, REVIEW_ACTION_REJECT}
            else params.action
        )
        if params.action == REVIEW_ACTION_REVISE and prior is not None:
            await record_feedback_correction(
                self._orchestrator,
                FeedbackCorrectionContext(
                    project_id=params.project_id,
                    prior=prior,
                    feedback=params.feedback,
                    persona=params.persona,
                    structured_feedback=params.structured_feedback,
                    db=params.db,
                ),
            )
        human_input: dict[str, object] = {
            "action": graph_action,
            "reviewer_id": params.reviewer_id,
            "feedback": params.feedback,
        }
        if params.structured_feedback:
            human_input[STRUCTURED_FEEDBACK_KEY] = params.structured_feedback
        state = await self._orchestrator.resume(
            params.project_id,
            human_input,
            db=params.db,
            workflow_input=workflow_input,
        )
        persisted = await self._orchestrator.get_state(params.project_id)
        if persisted is not None:
            state = persisted
        await self._sync_project_phase(params.db, params.project_id, state)
        if (
            params.db is not None
            and prior is not None
            and str(prior.get("current_phase", "")) == PHASE_IMAGES
            and params.action == REVIEW_ACTION_APPROVE
        ):
            from rag_backend.application.services.carousel.editorial_finalize import (
                finalize_carousel_after_images_approval,
            )

            await finalize_carousel_after_images_approval(params.db, params.project_id)
        await emit_review_event(
            ReviewEventEmitRequest(
                db=params.db,
                event_service=self._events,
                notification_service=self._notifications,
                context=ReviewEventEmitContext(
                    project_id=params.project_id,
                    action=params.action,
                    reviewer_id=params.reviewer_id,
                    feedback=params.feedback,
                    prior=prior,
                    state=state,
                ),
            ),
        )
        await publish_workflow_sse_updates(params.project_id, state)
        return state

    async def get_workflow_state(
        self,
        project_id: str,
        db: AsyncSession | None = None,
    ) -> CarouselWorkflowState | None:
        """Load workflow state from checkpointer; merge DB phase_status when DB says in_progress."""
        state = await self._orchestrator.get_state(project_id)
        if state is None or not str(state.get("current_phase", "")).strip():
            return None
        if db is not None:
            project = await db.get(CarouselProjectModel, project_id)
            if (
                project is not None
                and str(project.phase_status) == PHASE_STATUS_IN_PROGRESS
                and str(state.get("phase_status", "")) == PHASE_STATUS_AWAITING_HUMAN
            ):
                state["phase_status"] = PHASE_STATUS_IN_PROGRESS
        return state

    async def mark_resume_in_progress(
        self,
        project_id: str,
        db: AsyncSession | None,
    ) -> str:
        """Set workflow to in_progress and broadcast SSE before background resume."""
        prior = await self.get_workflow_state(project_id)
        current_phase = str(prior.get("current_phase", "")) if prior else ""
        in_progress_state: CarouselWorkflowState = {
            **(prior or {}),
            "project_id": project_id,
            "current_phase": current_phase,
            "phase_status": PHASE_STATUS_IN_PROGRESS,
        }
        await self._sync_project_phase(db, project_id, in_progress_state)
        from rag_backend.application.services.carousel.editorial_workflow_support import (
            publish_workflow_phase_change,
        )

        await publish_workflow_phase_change(
            project_id,
            current_phase,
            PHASE_STATUS_IN_PROGRESS,
        )
        return current_phase

    async def publish_resume_error_event(
        self,
        project_id: str,
        *,
        message: str,
        recoverable: bool,
    ) -> None:
        """Publish recoverable workflow error after background resume failure."""
        prior = await self.get_workflow_state(project_id)
        phase = str(prior.get("current_phase", "")) if prior else ""
        from rag_backend.application.services.carousel.editorial_workflow_support import (
            PublishParams,
            publish_workflow_error,
        )

        await publish_workflow_error(
            PublishParams(project_id=project_id, phase=phase),
            message,
            recoverable=recoverable,
        )

    async def stream_phase_updates(
        self,
        project_id: str,
        *,
        phase_progress: dict[str, object] | None = None,
    ) -> AsyncIterator[dict[str, object]]:
        """Yield workflow phase and progress events for SSE consumers."""
        async for event in stream_workflow_phase_updates(
            self._orchestrator,
            project_id,
            phase_progress=phase_progress,
        ):
            yield event


__all__ = [
    "EditorialWorkflowConfig",
    "EditorialWorkflowService",
    "EditorialWorkflowStartInput",
    "ReviewEventEmitContext",
]
