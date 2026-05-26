"""Carousel content generation sub-agent.

Orchestrates the 7-phase carousel pipeline:
1. Research - Parallel web scraping
2. Title Optimization - LLM-based title improvement
3. Content Synthesis - Slide-by-slide content generation
4. Design System - Color palette and HTML template
5. Image Generation - Gemini API for comic/manga style images
6. Assembly & Export - Playwright HTML to JPG
7. Caption Generation - Instagram caption with hashtags
"""

import asyncio
from collections.abc import AsyncIterator, Callable
from datetime import datetime
from pathlib import Path
from typing import ClassVar
from uuid import UUID

from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.application.services.carousel.graph import CarouselDeps, build_graph
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.application.services.carousel.types import unpack_extras
from rag_backend.application.services.carousel_refinement import (
    CarouselRefinementMixin,
)
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.application.services.linkedin_post_generator import (
    LinkedInPostGenerator,
)
from rag_backend.application.services.pdf_slide_builder import PdfSlideBuilder
from rag_backend.domain.constants.retry import LANGGRAPH_MAX_ATTEMPTS
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import (
    CarouselExportService,
    CarouselRepository,
    LLMService,
    ResearchTool,
)
from rag_backend.domain.retry import retry_async
from rag_backend.domain.types import PipelineEvent
from rag_backend.infrastructure.logging import get_logger
from rag_backend.monitoring_langfuse import get_langfuse_handler

from ._constants import (
    _ERR_NO_CHECKPOINTER,
    _ERR_NO_OUTPUT_DIR,
    _ERR_NO_SLIDES,
    _ERR_PROJECT_NOT_FOUND,
)
from .graph import _run_graph_body, _run_graph_producer
from .phases import (
    _phase1_research,
    _phase2_3_content,
    _phase4_design,
    _phase5_images,
    _phase6_bilingual_export,
    _phase7_caption,
    _phase8_linkedin,
    _render_language,
    _resolve_theme,
    _set_progress,
)

logger = get_logger()

__all__ = [
    "_ERR_NO_CHECKPOINTER",
    "_ERR_NO_OUTPUT_DIR",
    "_ERR_NO_SLIDES",
    "_ERR_PROJECT_NOT_FOUND",
    "CarouselAgent",
]


class CarouselAgent(CarouselRefinementMixin):
    """Sub-agent specialized in carousel content generation."""

    # Class-level registries so graph execution survives HTTP disconnects.
    # `_tasks` holds the background asyncio.Task running the graph;
    # `_queues` holds an asyncio.Queue that pipes events from the runner
    # to every active SSE consumer.
    _tasks: ClassVar[dict[str, asyncio.Task[None]]] = {}
    _queues: ClassVar[dict[str, asyncio.Queue[PipelineEvent]]] = {}

    # Phase and graph methods — implemented in sibling modules.
    _phase1_research = _phase1_research
    _phase2_3_content = _phase2_3_content
    _phase4_design = _phase4_design
    _phase5_images = _phase5_images
    _phase6_bilingual_export = _phase6_bilingual_export
    _render_language = _render_language
    _phase7_caption = _phase7_caption
    _phase8_linkedin = _phase8_linkedin
    _resolve_theme = _resolve_theme
    _set_progress = _set_progress
    _run_graph_body = _run_graph_body
    _run_graph_producer = _run_graph_producer

    def __init__(
        self,
        repository: CarouselRepository,
        llm_service: LLMService,
        research_tool: ResearchTool,
        image_registry: ImageProviderRegistry,
        export_service: CarouselExportService,
        linkedin_post_generator: LinkedInPostGenerator | None = None,
        pdf_slide_builder: PdfSlideBuilder | None = None,
        output_base_dir: str = "./output/carousels",
        checkpointer: BaseCheckpointSaver[object] | None = None,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
        repository_factory: Callable[[AsyncSession], CarouselRepository] | None = None,
    ) -> None:
        self._repo = repository
        self._llm = llm_service
        self._research = research_tool
        self._image_registry = image_registry
        self._export = export_service
        self._linkedin_post_generator = linkedin_post_generator
        self._pdf_slide_builder = pdf_slide_builder
        self._output_base = Path(output_base_dir)
        self._template = CarouselTemplateBuilder()
        self._checkpointer = checkpointer
        self._session_maker = session_maker
        self._repository_factory = repository_factory

    @staticmethod
    def _thread_id(project_id: UUID) -> str:
        return f"carousel-{project_id}"

    def _build_deps(self, repo: CarouselRepository | None = None) -> CarouselDeps:
        return CarouselDeps(
            repo=repo or self._repo,
            llm=self._llm,
            research_tool=self._research,
            image_registry=self._image_registry,
            export=self._export,
            template=self._template,
            linkedin_generator=self._linkedin_post_generator,
            pdf_builder=self._pdf_slide_builder,
        )

    def to_subagent(
        self, output_base_dir: str = "./output/carousels"
    ) -> dict[str, object]:
        from rag_backend.application.services.carousel.subagent import (
            build_carousel_subagent,
        )

        return build_carousel_subagent(
            self._build_deps(),
            checkpointer=self._checkpointer,
            output_base_dir=output_base_dir,
        )

    async def execute_pipeline(
        self,
        project_id: UUID,
        seed_urls: list[str] | None = None,
    ) -> CarouselProject:
        project = await self._repo.get_project_by_id(project_id)
        if project is None:
            raise ValueError(_ERR_PROJECT_NOT_FOUND.format(project_id))

        output_dir = self._output_base / str(project_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        graph = build_graph(self._build_deps(), checkpointer=self._checkpointer)
        initial_state: PipelineState = {
            "project_id": project_id,
            "seed_urls": seed_urls or [],
            "output_dir": str(output_dir),
            "project": project,
        }
        lf_handler = get_langfuse_handler()
        base_config: dict[str, object] = {}
        if self._checkpointer is not None:
            base_config["configurable"] = {"thread_id": self._thread_id(project_id)}
        if lf_handler is not None:
            base_config["callbacks"] = [lf_handler]
        config: RunnableConfig | None = base_config if base_config else None

        try:
            async for attempt in retry_async(attempts=LANGGRAPH_MAX_ATTEMPTS):
                with attempt:
                    final_state = await graph.ainvoke(initial_state, config=config)
        except Exception as exc:
            latest_project = await self._repo.get_project_by_id(project_id)
            if latest_project is None:
                latest_project = project
            latest_project.mark_failed(str(exc))
            await self._repo.update_project(latest_project)
            raise

        final_project: CarouselProject = final_state["project"]
        return final_project

    def start_pipeline(
        self,
        project_id: UUID,
        seed_urls: list[str] | None = None,
    ) -> None:
        thread_id = self._thread_id(project_id)
        if thread_id not in self._tasks or self._tasks[thread_id].done():
            queue: asyncio.Queue[PipelineEvent] = asyncio.Queue(maxsize=100)
            self._queues[thread_id] = queue
            self._tasks[thread_id] = asyncio.create_task(
                self._run_graph_producer(project_id, seed_urls, queue)
            )

    async def stream_pipeline(
        self,
        project_id: UUID,
        seed_urls: list[str] | None = None,
    ) -> AsyncIterator[PipelineEvent]:
        self.start_pipeline(project_id, seed_urls)
        thread_id = self._thread_id(project_id)
        queue = self._queues[thread_id]

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=5.0)
            except TimeoutError:
                task = self._tasks.get(thread_id)
                if task is not None and task.done():
                    final_project = await self._repo.get_project_by_id(project_id)
                    yield {
                        "node": "end",
                        "status": final_project.status.value
                        if final_project
                        else "completed",
                        "phase_progress": final_project.phase_progress
                        if final_project
                        else None,
                    }
                    break
                continue

            yield event
            if event.get("node") in {"end", "error"}:
                break

    async def resume_pipeline(self, project_id: UUID) -> CarouselProject:
        if self._checkpointer is None:
            raise RuntimeError(_ERR_NO_CHECKPOINTER)
        project = await self._repo.get_project_by_id(project_id)
        if project is None:
            raise ValueError(_ERR_PROJECT_NOT_FOUND.format(project_id))

        output_dir = self._output_base / str(project_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        graph = build_graph(self._build_deps(), checkpointer=self._checkpointer)
        config = {"configurable": {"thread_id": self._thread_id(project_id)}}

        has_checkpoint = False
        try:
            snapshot = await graph.aget_state(config)
            has_checkpoint = snapshot is not None and bool(snapshot.values)
        except Exception:
            has_checkpoint = False

        input_state = (
            None
            if has_checkpoint
            else {
                "project_id": project_id,
                "seed_urls": [],
                "output_dir": str(output_dir),
                "project": project,
            }
        )

        try:
            async for attempt in retry_async(attempts=LANGGRAPH_MAX_ATTEMPTS):
                with attempt:
                    final_state = await graph.ainvoke(input_state, config=config)
        except Exception as exc:
            project.mark_failed(str(exc))
            await self._repo.update_project(project)
            raise

        final_project: CarouselProject = final_state["project"]
        return final_project

    async def re_render_slides(self, project_id: UUID) -> CarouselProject:
        project = await self._repo.get_project_by_id(project_id)
        if project is None:
            raise ValueError(_ERR_PROJECT_NOT_FOUND.format(project_id))
        if not project.output_dir:
            raise ValueError(_ERR_NO_OUTPUT_DIR.format(project_id))
        slides = await self._repo.get_slides_by_project(project_id)
        if not slides:
            raise ValueError(_ERR_NO_SLIDES.format(project_id))

        slides_data = [unpack_extras(s) for s in slides]
        pt_html = self._phase4_design(project, slides_data)
        await self._phase6_bilingual_export(
            project, slides_data, pt_html, Path(project.output_dir)
        )
        project.updated_at = datetime.utcnow()
        return await self._repo.update_project(project)
