"""Editorial carousel workflow orchestration (AI-004 + Phase 3 WF-*)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.carousel_editorial_orchestrator import (
    CarouselEditorialOrchestrator,
)
from rag_backend.application.services.carousel.editorial_workflow_events import (
    emit_phase_event,
    emit_review_event,
)
from rag_backend.application.services.carousel.editorial_workflow_service_helpers import (
    prepare_resume_workflow,
    record_feedback_correction,
    stream_workflow_phase_updates,
    validate_revision_cap,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
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
    PHASE_RESEARCH,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    REVIEW_ACTION_REJECT,
    REVIEW_ACTION_REVISE,
    STRUCTURED_FEEDBACK_KEY,
    WORKFLOW_METADATA_EDITORIAL_7_PHASE,
    WORKFLOW_TRACE_PHASE_HUMAN_REVIEW,
    WORKFLOW_TRACE_PHASE_REVIEW,
)
from rag_backend.domain.constants.workflow_validation import CONTENT_TYPE_CAROUSEL
from rag_backend.domain.models.carousels import ReviewEventParams
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.monitoring_langfuse import (
    create_workflow_trace,
    propagate_attributes,
    record_human_review,
)


class EditorialWorkflowService:
    """Coordinates AI agents, LangGraph workflow, events, and Langfuse tracing."""

    def __init__(
        self,
        llm: BaseChatModel,
        checkpointer: object | None = None,
        event_service: WorkflowEventService | None = None,
        notification_service: NotificationService | None = None,
        image_registry: ImageProviderRegistry | None = None,
    ) -> None:
        self._llm = llm
        self._orchestrator = CarouselEditorialOrchestrator(
            llm=llm,
            checkpointer=checkpointer,
            image_registry=image_registry,
        )
        self._events = event_service
        self._notifications = notification_service or NotificationService()

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
            project_id=UUID(project_id),
            user_id=workflow_input.user_id,
            content_type=CONTENT_TYPE_CAROUSEL,
            metadata={"workflow": WORKFLOW_METADATA_EDITORIAL_7_PHASE},
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
            project_id=project_id,
            state=state,
            user_id=workflow_input.user_id,
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
            from rag_backend.domain.models import CarouselStatus

            project.status = CarouselStatus.FAILED.value
        raw_workflow_status = state.get("workflow_status")
        if raw_workflow_status is not None:
            project.workflow_status = str(raw_workflow_status)
        await db.flush()

    async def resume_workflow(
        self,
        project_id: str,
        action: str,
        reviewer_id: str,
        feedback: str | None = None,
        db: AsyncSession | None = None,
        persona: PersonaProfile | None = None,
        project_title: str = "",
        structured_feedback: dict[str, object] | None = None,
    ) -> CarouselWorkflowState:
        """Resume workflow after human review."""
        prior = await self._orchestrator.get_state(project_id)
        if action == REVIEW_ACTION_REVISE and prior is not None:
            await validate_revision_cap(
                prior,
                db=db,
                notifications=self._notifications,
                project_id=project_id,
                project_title=project_title,
            )
        await prepare_resume_workflow(
            self._orchestrator,
            project_id,
            action,
            prior,
            feedback,
        )
        trace = create_workflow_trace(
            project_id=UUID(project_id),
            user_id=reviewer_id,
            content_type=CONTENT_TYPE_CAROUSEL,
            metadata={"phase": WORKFLOW_TRACE_PHASE_HUMAN_REVIEW},
        )
        if trace is not None:
            record_human_review(
                trace=trace,
                params=ReviewEventParams(
                    phase=WORKFLOW_TRACE_PHASE_REVIEW,
                    action=action,
                    reviewer_id=reviewer_id,
                    time_to_respond=None,
                    feedback=feedback,
                ),
            )
        workflow_input = EditorialWorkflowStartInput(
            topic="",
            audience="",
            brief="",
            sources=[],
            persona=persona,
            user_id=reviewer_id,
        )
        graph_action = (
            REVIEW_ACTION_REJECT
            if action in {REVIEW_ACTION_REVISE, REVIEW_ACTION_REJECT}
            else action
        )
        if action == REVIEW_ACTION_REVISE and prior is not None:
            await record_feedback_correction(
                orchestrator=self._orchestrator,
                db=db,
                project_id=project_id,
                prior=prior,
                persona=persona,
                feedback=feedback,
                structured_feedback=structured_feedback,
            )
        human_input: dict[str, object] = {
            "action": graph_action,
            "reviewer_id": reviewer_id,
            "feedback": feedback,
        }
        if structured_feedback:
            human_input[STRUCTURED_FEEDBACK_KEY] = structured_feedback
        state = await self._orchestrator.resume(
            project_id,
            human_input,
            db=db,
            workflow_input=workflow_input,
        )
        persisted = await self._orchestrator.get_state(project_id)
        if persisted is not None:
            state = persisted
        await self._sync_project_phase(db, project_id, state)
        await emit_review_event(
            db=db,
            event_service=self._events,
            notification_service=self._notifications,
            ctx=ReviewEventEmitContext(
                project_id=project_id,
                action=action,
                reviewer_id=reviewer_id,
                feedback=feedback,
                prior=prior,
                state=state,
            ),
        )
        await publish_workflow_sse_updates(project_id, state)
        return state

    async def get_workflow_state(self, project_id: str) -> CarouselWorkflowState | None:
        """Load persisted workflow state from checkpointer (WF-002)."""
        state = await self._orchestrator.get_state(project_id)
        if state is None:
            return None
        if not str(state.get("current_phase", "")).strip():
            return None
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
        await self._orchestrator.update_state(
            project_id,
            {"phase_status": PHASE_STATUS_IN_PROGRESS},
        )
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
            publish_workflow_error,
        )

        await publish_workflow_error(
            project_id,
            phase,
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
    "EditorialWorkflowService",
    "EditorialWorkflowStartInput",
    "ReviewEventEmitContext",
]
