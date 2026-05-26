"""Editorial carousel workflow orchestration (AI-004 + Phase 3 WF-*)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.agents.outline_agent import OutlineAgent
from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.agents.source_synthesis_agent import SourceSynthesisAgent
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.application.services.notification_service import NotificationService
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_OUTLINE,
    PHASE_RESEARCH,
    REVIEW_ACTION_APPROVE,
)
from rag_backend.domain.constants.notifications import (
    NOTIFICATION_TYPE_PHASE_APPROVED,
    NOTIFICATION_TYPE_PHASE_REJECTED,
)
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_PROJECT,
    EVENT_SOURCE_WORKFLOW_ENGINE,
    EVENT_TYPE_PROJECT_PHASE_CHANGED,
    EVENT_TYPE_PROJECT_REVIEW_COMPLETED,
    EVENT_TYPE_PROJECT_REVIEW_REQUESTED,
)
from rag_backend.domain.models.carousels import ReviewEventParams
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.monitoring_langfuse import (
    create_workflow_trace,
    propagate_attributes,
    record_human_review,
)


@dataclass(frozen=True)
class EditorialWorkflowStartInput:
    """Inputs required to start the editorial workflow."""

    topic: str
    audience: str
    brief: str
    sources: list[dict[str, str]]
    persona: PersonaProfile | None = None
    user_id: str = "system"
    reviewer_id: str | None = None


@dataclass(frozen=True)
class ReviewEventEmitContext:
    """Parameters for emitting carousel review workflow events."""

    project_id: str
    action: str
    reviewer_id: str
    feedback: str | None
    prior: CarouselWorkflowState | None
    state: CarouselWorkflowState


class EditorialWorkflowService:
    """Coordinates AI agents, LangGraph workflow, events, and Langfuse tracing."""

    def __init__(
        self,
        llm: BaseChatModel,
        checkpointer: object | None = None,
        event_service: WorkflowEventService | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._llm = llm
        self._engine = CarouselWorkflowEngine(checkpointer=checkpointer)
        self._source_agent = SourceSynthesisAgent(llm=llm)
        self._outline_agent = OutlineAgent(llm=llm)
        self._content_agent = ContentDraftAgent(llm=llm)
        self._events = event_service
        self._notifications = notification_service or NotificationService()

    async def start_workflow(
        self,
        project_id: str,
        workflow_input: EditorialWorkflowStartInput,
        db: AsyncSession | None = None,
    ) -> CarouselWorkflowState:
        """Run research synthesis, outline, and content phases before human gates."""
        trace = create_workflow_trace(
            project_id=UUID(project_id),
            user_id=workflow_input.user_id,
            content_type="carousel",
            metadata={"workflow": "editorial_7_phase"},
        )

        with propagate_attributes(
            metadata={"project_id": project_id, "phase": PHASE_RESEARCH},
        ):
            research_findings: list[dict[str, object]] = []
            for source in workflow_input.sources:
                extracted = await self._source_agent.extract_key_points(
                    title=source.get("title", ""),
                    content=source.get("content", ""),
                    source_type=source.get("source_type", "document"),
                )
                research_findings.append({
                    "source": source.get("title", ""),
                    **extracted,
                })

        with propagate_attributes(
            metadata={"project_id": project_id, "phase": PHASE_OUTLINE}
        ):
            source_texts = [s.get("content", "") for s in workflow_input.sources]
            outline = await self._outline_agent.generate_outline(
                topic=workflow_input.topic,
                audience=workflow_input.audience,
                brief=workflow_input.brief,
                sources=source_texts,
            )

        slide_drafts: list[dict[str, object]] = []
        with propagate_attributes(
            metadata={"project_id": project_id, "phase": PHASE_CONTENT}
        ):
            for slide in outline:
                if not isinstance(slide, dict):
                    continue
                draft = await self._content_agent.draft_slide(
                    slide_index=int(slide.get("slide_index", 0)),
                    title=str(slide.get("title", "")),
                    key_points=[
                        str(p)
                        for p in slide.get("key_points", [])
                        if isinstance(p, str)
                    ],
                    persona=workflow_input.persona,
                )
                slide_drafts.append({**slide, **draft})

        if workflow_input.persona is not None and slide_drafts:
            persona_agent = PersonaAgent(persona=workflow_input.persona, llm=self._llm)
            first_text = str(slide_drafts[0].get("draft_text", ""))
            voice_scores = await persona_agent.evaluate_match(first_text)
            if trace is not None:
                record_human_review(
                    trace=trace,
                    params=ReviewEventParams(
                        phase=PHASE_CONTENT,
                        action="voice_scored",
                        reviewer_id="ai",
                        time_to_respond=None,
                        feedback=str(voice_scores.get("overall", 0)),
                    ),
                )

        initial_brief = {
            "topic": workflow_input.topic,
            "audience": workflow_input.audience,
            "brief": workflow_input.brief,
            "sources": workflow_input.sources,
        }
        state = await self._engine.start(
            project_id,
            initial_brief,
            research_findings=research_findings,
            outline=outline,
            slide_drafts=slide_drafts,
        )
        await self._emit_phase_event(db, project_id, state, workflow_input.user_id)
        if db and workflow_input.reviewer_id:
            await self._notifications.create_review_request(
                db,
                user_id=workflow_input.reviewer_id,
                content_id=project_id,
                content_type="carousel",
                title=workflow_input.topic,
            )
        return state

    async def resume_workflow(
        self,
        project_id: str,
        action: str,
        reviewer_id: str,
        feedback: str | None = None,
        db: AsyncSession | None = None,
    ) -> CarouselWorkflowState:
        """Resume workflow after human review."""
        prior = await self._engine.get_state(project_id)
        trace = create_workflow_trace(
            project_id=UUID(project_id),
            user_id=reviewer_id,
            content_type="carousel",
            metadata={"phase": "human_review"},
        )
        if trace is not None:
            record_human_review(
                trace=trace,
                params=ReviewEventParams(
                    phase="review",
                    action=action,
                    reviewer_id=reviewer_id,
                    time_to_respond=None,
                    feedback=feedback,
                ),
            )
        human_input = {
            "action": action,
            "reviewer_id": reviewer_id,
            "feedback": feedback,
        }
        state = await self._engine.resume(project_id, human_input)
        await self._emit_review_event(
            db,
            ReviewEventEmitContext(
                project_id=project_id,
                action=action,
                reviewer_id=reviewer_id,
                feedback=feedback,
                prior=prior,
                state=state,
            ),
        )
        return state

    async def get_workflow_state(self, project_id: str) -> CarouselWorkflowState | None:
        """Load persisted workflow state from checkpointer (WF-002)."""
        return await self._engine.get_state(project_id)

    async def stream_phase_updates(
        self,
        project_id: str,
    ) -> AsyncIterator[dict[str, str]]:
        """Yield the current workflow phase for SSE consumers."""
        state = await self._engine.get_state(project_id)
        if state is None:
            return
        current_phase = str(state.get("current_phase", ""))
        if not current_phase:
            return
        yield {
            "event": "project.phase.changed",
            "project_id": project_id,
            "phase": current_phase,
            "phase_status": str(state.get("phase_status", "")),
        }

    async def _emit_phase_event(
        self,
        db: AsyncSession | None,
        project_id: str,
        state: CarouselWorkflowState,
        user_id: str,
    ) -> None:
        if db is None or self._events is None:
            return
        await self._events.emit(
            db,
            event_type=EVENT_TYPE_PROJECT_PHASE_CHANGED,
            aggregate_id=project_id,
            aggregate_type=AGGREGATE_TYPE_PROJECT,
            payload={
                "phase": str(state.get("current_phase", "")),
                "phase_status": str(state.get("phase_status", "")),
            },
            metadata={"user_id": user_id, "source": EVENT_SOURCE_WORKFLOW_ENGINE},
        )
        await self._events.emit(
            db,
            event_type=EVENT_TYPE_PROJECT_REVIEW_REQUESTED,
            aggregate_id=project_id,
            aggregate_type=AGGREGATE_TYPE_PROJECT,
            payload={"phase": str(state.get("current_phase", ""))},
            metadata={"user_id": user_id, "source": EVENT_SOURCE_WORKFLOW_ENGINE},
        )

    async def _emit_review_event(
        self,
        db: AsyncSession | None,
        ctx: ReviewEventEmitContext,
    ) -> None:
        if db is None or self._events is None:
            return
        old_phase = str(ctx.prior.get("current_phase", "")) if ctx.prior else ""
        new_phase = str(ctx.state.get("current_phase", ""))
        await self._events.emit(
            db,
            event_type=EVENT_TYPE_PROJECT_REVIEW_COMPLETED,
            aggregate_id=ctx.project_id,
            aggregate_type=AGGREGATE_TYPE_PROJECT,
            payload={
                "action": ctx.action,
                "feedback": ctx.feedback or "",
                "phase": new_phase,
            },
            metadata={
                "reviewer_id": ctx.reviewer_id,
                "source": EVENT_SOURCE_WORKFLOW_ENGINE,
            },
        )
        if old_phase != new_phase:
            await self._events.emit(
                db,
                event_type=EVENT_TYPE_PROJECT_PHASE_CHANGED,
                aggregate_id=ctx.project_id,
                aggregate_type=AGGREGATE_TYPE_PROJECT,
                payload={
                    "old_phase": old_phase,
                    "phase": new_phase,
                    "phase_status": str(ctx.state.get("phase_status", "")),
                },
                metadata={
                    "reviewer_id": ctx.reviewer_id,
                    "source": EVENT_SOURCE_WORKFLOW_ENGINE,
                },
            )
        notif_type = (
            NOTIFICATION_TYPE_PHASE_APPROVED
            if ctx.action == REVIEW_ACTION_APPROVE
            else NOTIFICATION_TYPE_PHASE_REJECTED
        )
        await self._notifications.create_workflow_update(
            db,
            user_id=ctx.reviewer_id,
            notification_type=notif_type,
            title=f"Phase {ctx.action}: {new_phase}",
            body=ctx.feedback or "",
            content_id=ctx.project_id,
            content_type="carousel",
        )


__all__ = ["EditorialWorkflowService", "EditorialWorkflowStartInput"]
