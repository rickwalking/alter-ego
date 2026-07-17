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
    CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
    PHASE_IMAGES,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REJECT,
    REVIEW_ACTION_REVISE,
    STRUCTURED_FEEDBACK_KEY,
    WORKFLOW_METADATA_EDITORIAL_7_PHASE,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
    WORKFLOW_TRACE_PHASE_HUMAN_REVIEW,
    WORKFLOW_TRACE_PHASE_REVIEW,
)
from rag_backend.domain.constants.workflow_validation import CONTENT_TYPE_CAROUSEL
from rag_backend.domain.models.carousels import ReviewEventParams
from rag_backend.domain.models.research_enrichment import ResearchEnrichmentParams
from rag_backend.domain.protocols import ResearchTool
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.monitoring_langfuse import (
    _TraceConfig,
    create_workflow_trace,
    propagate_attributes,
    record_human_review,
)
from rag_backend.modules.editorial.public import CarouselProjectWriteOwner


@dataclass
class EditorialWorkflowConfig:
    """Configuration bundle for EditorialWorkflowService."""

    llm: BaseChatModel
    checkpointer: object | None = None
    event_service: WorkflowEventService | None = None
    notification_service: NotificationService | None = None
    image_registry: ImageProviderRegistry | None = None
    # AE-0317: enables deterministic web-research enrichment at workflow start;
    # None (CI, tests, kill switch) means sources pass through unchanged.
    research_tool: ResearchTool | None = None


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
        self._research_tool = config.research_tool

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
            enriched_sources = await self._orchestrator.enrich_research_sources(
                workflow_input.sources,
                ResearchEnrichmentParams(
                    topic=workflow_input.topic,
                    research_tool=self._research_tool,
                ),
            )
            research_findings = await self._orchestrator.synthesize_research(
                enriched_sources,
            )

        initial_brief = {
            "topic": workflow_input.topic,
            "audience": workflow_input.audience,
            "brief": workflow_input.brief,
            "sources": enriched_sources,
        }
        overrides: dict[str, object] = {"research_findings": research_findings}
        policy_version = await self._resolve_presentation_policy_version(db, project_id)
        if policy_version:
            # AE-0311 deliverable 3: seed the project's stamped policy version so
            # a v2 project fires casing rules live at the content-review gate.
            overrides["presentation_policy_version"] = policy_version
        state = await self._orchestrator.start(
            project_id,
            initial_brief,
            **overrides,
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
                await CarouselProjectWriteOwner(db).assign_reviewer(
                    project_id,
                    workflow_input.reviewer_id,
                )
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

    @staticmethod
    async def _resolve_presentation_policy_version(
        db: AsyncSession | None,
        project_id: str,
    ) -> str | None:
        """Read the project's stamped presentation policy version (None → v1)."""
        if db is None:
            return None
        project = await db.get(CarouselProjectModel, project_id)
        if project is None:
            return None
        version = project.presentation_policy_version
        return version if isinstance(version, str) and version.strip() else None

    async def read_checkpoint_phase(self, project_id: str) -> str:
        """Return checkpoint phase for structured feedback validation."""
        return await read_engine_checkpoint_phase(
            self._orchestrator.engine,
            project_id,
        )

    @property
    def events(self) -> WorkflowEventService | None:
        """The workflow event service (audit + outbox), shared with AE-0311."""
        return self._events

    async def update_workflow_state(
        self,
        project_id: str,
        values: dict[str, object],
    ) -> None:
        """Patch checkpoint state through the engine wrapper (AE-0311 repair).

        Routes to ``CarouselWorkflowEngine.update_state`` (``as_node`` inferred
        from the pending interrupt) so the repair's checkpoint write shares the
        interrupt-preserving path and never hits the ``as_node=None`` clearing
        footgun on approved-hold threads.
        """
        await self._orchestrator.update_state(project_id, values)

    async def patch_parked_checkpoint(
        self,
        project_id: str,
        values: dict[str, object],
    ) -> bool:
        """Patch a parked/held checkpoint without advancing the node (AE-0314).

        The completed-project slide edit converges the checkpoint (source-of-
        truth option (a)) on the approved-hold thread via ``as_node=None`` so the
        pending interrupt is preserved. Returns ``True`` when a parked checkpoint
        was patched; ``False`` for legacy END-state/absent threads (the
        projection-only fallback).
        """
        return await self._orchestrator.patch_parked_checkpoint(project_id, values)

    @staticmethod
    async def _sync_project_phase(
        db: AsyncSession | None,
        project_id: str,
        state: CarouselWorkflowState,
    ) -> None:
        """Keep carousel project row in sync with workflow state for the Kanban board.

        Routes the workflow-owned phase columns through the single write owner
        (AE-0107); the owner only ``flush``\\es, so the commit stays with the
        caller (the route's UoW commit or the background runner).
        """
        if db is None:
            return
        await CarouselProjectWriteOwner(db).sync_phase(project_id, state)

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
                    structured_feedback=params.structured_feedback,
                ),
            )
        await prepare_resume_workflow(
            ResumeContext(
                orchestrator=self._orchestrator,
                project_id=params.project_id,
                action=params.action,
                prior=prior,
                feedback=params.feedback,
                structured_feedback=params.structured_feedback,
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
            # AE-0261: a revision on the image phase must change the rendered
            # scene, otherwise the per-prompt reuse hash matches and the same
            # image is returned. Persist the feedback as custom visual direction
            # BEFORE the graph re-runs the image node (which reloads the project).
            if (
                params.db is not None
                and params.feedback
                and str(prior.get("current_phase", "")) == PHASE_IMAGES
            ):
                await self._append_image_visual_feedback(
                    params.db, params.project_id, params.feedback
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

    @staticmethod
    async def _append_image_visual_feedback(
        db: AsyncSession, project_id: str, feedback: str
    ) -> None:
        """Append image-phase revision feedback to custom visual direction.

        Persisted before the graph re-runs so the image node (which reloads
        the project) renders a different scene and bypasses prompt reuse.
        """
        note = feedback.strip()
        if not note:
            return
        project = await db.get(CarouselProjectModel, project_id)
        if project is None:
            return
        existing = (project.custom_visual_details or "").strip()
        project.custom_visual_details = f"{existing}. {note}" if existing else note
        await db.commit()

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
        # AE-0288: resuming an already-approved carousel (a final-review
        # send-back) must drop the DB publish lock synchronously — before the
        # 202 returns — so a concurrent publish cannot ship stale content while
        # the workflow re-runs in the background. The later final_review re-gate
        # restores approved_for_publish once the revision is re-approved.
        if (
            str((prior or {}).get("workflow_status", ""))
            == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
        ):
            in_progress_state["workflow_status"] = (
                CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT
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
        # AE-0315: the before_update listener stamped run_started_at inside the
        # same flush that flipped phase_status; surface it on run.started so
        # the client shows the banner within seconds of the 202.
        await self._publish_run_started(db, project_id, current_phase)
        return current_phase

    @staticmethod
    async def _publish_run_started(
        db: AsyncSession | None,
        project_id: str,
        current_phase: str,
    ) -> None:
        """Broadcast run.started with the freshly stamped run_started_at."""
        from rag_backend.application.services.carousel.editorial_workflow_run_events import (
            publish_run_started,
        )

        run_started_at = None
        if db is not None:
            project = await db.get(CarouselProjectModel, project_id)
            if project is not None:
                run_started_at = project.run_started_at
        await publish_run_started(project_id, current_phase, run_started_at)

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
