"""Editorial carousel orchestrator wrapping LangGraph workflow (CP-005)."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.agents.outline_agent import OutlineAgent
from rag_backend.agents.source_synthesis_agent import SourceSynthesisAgent
from rag_backend.application.services.carousel.editorial_workflow_generators import (
    synthesize_research,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)


class CarouselEditorialOrchestrator:
    """Coordinates phase generation, LangGraph gates, and subagent metadata."""

    def __init__(
        self,
        llm: BaseChatModel,
        checkpointer: object | None = None,
        image_registry: ImageProviderRegistry | None = None,
    ) -> None:
        self._llm = llm
        self._artifact_runner = PhaseArtifactRunner(
            outline_agent=OutlineAgent(llm=llm),
            content_agent=ContentDraftAgent(llm=llm),
            llm=llm,
            image_registry=image_registry,
        )
        self._engine = CarouselWorkflowEngine(
            checkpointer=checkpointer,
            artifact_runner=self._artifact_runner,
        )
        self._source_agent = SourceSynthesisAgent(llm=llm)

    @property
    def engine(self) -> CarouselWorkflowEngine:
        return self._engine

    async def synthesize_research(
        self,
        sources: list[dict[str, str]],
    ) -> list[dict[str, object]]:
        return await synthesize_research(self._source_agent, sources)

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

    async def get_state(self, project_id: str) -> CarouselWorkflowState | None:
        return await self._engine.get_state(project_id)

    async def update_state(
        self,
        project_id: str,
        values: dict[str, object],
    ) -> None:
        await self._engine.update_state(project_id, values)


__all__ = ["CarouselEditorialOrchestrator"]
