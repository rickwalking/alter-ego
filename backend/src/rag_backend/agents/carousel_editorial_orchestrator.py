"""Editorial carousel orchestrator wrapping LangGraph workflow (CP-005)."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.agents.outline_agent import OutlineAgent
from rag_backend.agents.research_enrichment import enrich_sources
from rag_backend.agents.source_synthesis_agent import SourceSynthesisAgent
from rag_backend.application.services.carousel.editorial_workflow_generators import (
    synthesize_research,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    ChatModelRoles,
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
    PhaseArtifactRunnerConfig,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.domain.protocols import ResearchEnrichmentParams
from rag_backend.infrastructure.monitoring_langfuse import get_langfuse_runnable_config


class CarouselEditorialOrchestrator:
    """Coordinates phase generation, LangGraph gates, and subagent metadata."""

    def __init__(
        self,
        llm: BaseChatModel | ChatModelRoles,
        checkpointer: object | None = None,
        image_registry: ImageProviderRegistry | None = None,
    ) -> None:
        """Wire the phase agents to their per-role models.

        Research and outline run on the reasoning model; drafting, persona scoring and
        distribution copy (translation, caption) run on the fast model. The field repair
        of a blocked content gate also runs on the fast model and is traced in Langfuse.
        """
        roles = ChatModelRoles.coerce(llm)
        self._llm = roles.fast
        self._artifact_runner = PhaseArtifactRunner(
            PhaseArtifactRunnerConfig(
                outline_agent=OutlineAgent(llm=roles.reasoning),
                content_agent=ContentDraftAgent(llm=roles.fast),
                llm=roles.fast,
                image_registry=image_registry,
                draft_concurrency=roles.draft_concurrency,
                gate_repair_tracing=get_langfuse_runnable_config,
            )
        )
        self._engine = CarouselWorkflowEngine(
            checkpointer=checkpointer,
            artifact_runner=self._artifact_runner,
        )
        self._source_agent = SourceSynthesisAgent(llm=roles.reasoning)

    @property
    def engine(self) -> CarouselWorkflowEngine:
        return self._engine

    async def synthesize_research(
        self,
        sources: list[dict[str, str]],
    ) -> list[dict[str, object]]:
        return await synthesize_research(self._source_agent, sources)

    async def enrich_research_sources(
        self,
        sources: list[dict[str, str]],
        params: ResearchEnrichmentParams,
    ) -> list[dict[str, str]]:
        """Deterministic scrape + topic-search enrichment pre-synthesis."""
        return await enrich_sources(sources, params)

    def _bind_resume_context(
        self,
        *,
        db: AsyncSession | None,
        workflow_input: EditorialWorkflowStartInput | None,
    ) -> None:
        scoped = self._artifact_runner.with_context(
            db=db,
            workflow_input=workflow_input,
        )
        self._engine.set_artifact_runner(scoped)

    async def start(
        self,
        project_id: str,
        brief: dict[str, object] | None = None,
        *,
        db: AsyncSession | None = None,
        workflow_input: EditorialWorkflowStartInput | None = None,
        **state_overrides: object,
    ) -> CarouselWorkflowState:
        self._bind_resume_context(db=db, workflow_input=workflow_input)
        return await self._engine.start(project_id, brief, **state_overrides)

    async def resume(
        self,
        project_id: str,
        human_input: dict[str, object] | None = None,
        *,
        db: AsyncSession | None = None,
        workflow_input: EditorialWorkflowStartInput | None = None,
    ) -> CarouselWorkflowState:
        self._bind_resume_context(db=db, workflow_input=workflow_input)
        return await self._engine.resume(project_id, human_input)

    async def continue_pending(
        self,
        project_id: str,
        *,
        db: AsyncSession | None = None,
        workflow_input: EditorialWorkflowStartInput | None = None,
    ) -> CarouselWorkflowState:
        """Re-run a parked pending node with the resume context bound."""
        self._bind_resume_context(db=db, workflow_input=workflow_input)
        return await self._engine.continue_pending(project_id)

    async def get_state(self, project_id: str) -> CarouselWorkflowState | None:
        return await self._engine.get_state(project_id)

    async def update_state(
        self,
        project_id: str,
        values: dict[str, object],
    ) -> None:
        await self._engine.update_state(project_id, values)

    async def patch_parked_checkpoint(
        self,
        project_id: str,
        values: dict[str, object],
    ) -> bool:
        return await self._engine.patch_parked_checkpoint(project_id, values)


__all__ = ["CarouselEditorialOrchestrator"]
