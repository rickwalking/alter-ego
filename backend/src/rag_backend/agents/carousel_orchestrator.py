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

from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.application.services.carousel.graph import CarouselDeps, build_graph
from rag_backend.application.services.carousel.nodes.caption import run_caption
from rag_backend.application.services.carousel.nodes.content import run_content
from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.nodes.export import (
    render_language,
    run_bilingual_export,
)
from rag_backend.application.services.carousel.nodes.images import run_images
from rag_backend.application.services.carousel.nodes.linkedin import run_linkedin
from rag_backend.application.services.carousel.nodes.progress import set_progress
from rag_backend.application.services.carousel.nodes.research import run_research
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.application.services.carousel.theme_resolver import resolve_theme
from rag_backend.application.services.carousel.types import (
    SlideData,
    unpack_extras,
)
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
from rag_backend.domain.models import (
    CarouselProject,
    ResearchSource,
)
from rag_backend.domain.protocols import (
    CarouselExportService,
    CarouselRepository,
    LLMService,
    ResearchTool,
)
from rag_backend.domain.types import PipelineEvent
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_ERR_PROJECT_NOT_FOUND = "Carousel project {} not found"
_ERR_NO_CHECKPOINTER = "resume_pipeline requires a checkpointer; none was injected"
_ERR_NO_OUTPUT_DIR = "Carousel project {} has no output_dir; cannot re-render slides."
_ERR_NO_SLIDES = "Carousel project {} has no slides."


class CarouselAgent(CarouselRefinementMixin):
    """Sub-agent specialized in carousel content generation."""

    # Class-level registries so graph execution survives HTTP disconnects.
    # `_tasks` holds the background asyncio.Task running the graph;
    # `_queues` holds an asyncio.Queue that pipes events from the runner
    # to every active SSE consumer.
    _tasks: ClassVar[dict[str, asyncio.Task[None]]] = {}
    _queues: ClassVar[dict[str, asyncio.Queue[PipelineEvent]]] = {}

    def __init__(  # noqa: PLR0913 — agent requires all pipeline dependencies
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
        """Deterministic thread_id keyed on project_id.

        Calling `/generate` and then `/resume` both use this id, so the
        resume path picks up the same checkpoint thread.
        """
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

    def to_subagent(self, output_base_dir: str = "./output/carousels") -> dict[str, object]:
        """Return a DeepAgents-compatible ``CompiledSubAgent`` dict.

        Allows the carousel pipeline to be registered as a subagent under
        a parent RAG agent, so complex carousel requests are delegated
        via the ``task`` tool instead of cluttering the parent toolset.
        """
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
        """Execute the full carousel generation pipeline via LangGraph.

        Loads the project, builds the StateGraph from the injected
        dependencies, and invokes it. The outer try/except preserves the
        `mark_failed` semantics: any node exception flips the project
        into FAILED and persists before re-raising.
        """
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
        config = (
            {"configurable": {"thread_id": self._thread_id(project_id)}}
            if self._checkpointer is not None
            else None
        )

        try:
            final_state = await graph.ainvoke(initial_state, config=config)
        except Exception as exc:
            # Re-fetch so we capture the phase_progress that was updated
            # inside the LangGraph state (the original `project` is stale).
            latest_project = await self._repo.get_project_by_id(project_id)
            if latest_project is None:
                latest_project = project
            latest_project.mark_failed(str(exc))
            await self._repo.update_project(latest_project)
            raise

        final_project: CarouselProject = final_state["project"]
        return final_project

    async def _run_graph_body(
        self,
        project_id: UUID,
        seed_urls: list[str] | None,
        queue: asyncio.Queue[PipelineEvent],
        repo: CarouselRepository,
    ) -> None:
        """Actual graph execution using the provided *repo*.

        Extracted so ``_run_graph_producer`` can swap in a fresh-session
        repository for background tasks.
        """
        project = await repo.get_project_by_id(project_id)
        if project is None:
            await queue.put(
                {
                    "node": "error",
                    "status": "failed",
                    "phase_progress": None,
                    "error": _ERR_PROJECT_NOT_FOUND.format(project_id),
                }
            )
            return

        output_dir = self._output_base / str(project_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        graph = build_graph(self._build_deps(repo=repo), checkpointer=self._checkpointer)
        initial_state: PipelineState = {
            "project_id": project_id,
            "seed_urls": seed_urls or [],
            "output_dir": str(output_dir),
            "project": project,
        }
        config = (
            {"configurable": {"thread_id": self._thread_id(project_id)}}
            if self._checkpointer is not None
            else None
        )

        await queue.put(
            {
                "node": "start",
                "status": project.status.value,
                "phase_progress": project.phase_progress,
            }
        )

        has_checkpoint = False
        if config is not None:
            try:
                snapshot = await graph.aget_state(config)
                has_checkpoint = snapshot is not None and bool(snapshot.values)
            except Exception:
                has_checkpoint = False

        try:
            stream_input = None if has_checkpoint else initial_state
            async for update in graph.astream(stream_input, config=config):
                for node_name, partial in update.items():
                    snapshot = partial.get("project") if isinstance(partial, dict) else None
                    if snapshot is None:
                        continue
                    await queue.put(
                        {
                            "node": node_name,
                            "status": snapshot.status.value,
                            "phase_progress": snapshot.phase_progress,
                        }
                    )
        except Exception as exc:
            latest_project = await repo.get_project_by_id(project_id)
            if latest_project is None:
                latest_project = project
            latest_project.mark_failed(str(exc))
            await repo.update_project(latest_project)
            await queue.put(
                {
                    "node": "error",
                    "status": latest_project.status.value,
                    "phase_progress": latest_project.phase_progress,
                    "error": str(exc),
                }
            )
            return

        final_project = await repo.get_project_by_id(project_id)
        await queue.put(
            {
                "node": "end",
                "status": final_project.status.value if final_project else "completed",
                "phase_progress": final_project.phase_progress if final_project else None,
            }
        )

    async def _run_graph_producer(
        self,
        project_id: UUID,
        seed_urls: list[str] | None,
        queue: asyncio.Queue[PipelineEvent],
    ) -> None:
        """Background task that runs the graph and feeds events into *queue*.

        When ``session_maker`` was injected (production), a fresh session is
        created for the background task so the graph survives the HTTP
        response lifecycle. Tests that don't pass a session_maker fall back
        to ``self._repo`` (usually a mock).
        """
        if self._session_maker is not None and self._repository_factory is not None:
            async with self._session_maker() as session:
                repo = self._repository_factory(session)
                await self._run_graph_body(project_id, seed_urls, queue, repo)
        else:
            await self._run_graph_body(project_id, seed_urls, queue, self._repo)

    def start_pipeline(
        self,
        project_id: UUID,
        seed_urls: list[str] | None = None,
    ) -> None:
        """Start the graph producer in the background if it is not already running.

        Idempotent: multiple calls for the same project_id are no-ops while
        the task is alive. Used by the non-blocking ``/resume`` route.
        """
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
        """Yield progress events from a background graph runner.

        Graph execution is decoupled from the HTTP connection so an SSE
        reconnect (or browser refresh) never cancels an in-flight LLM call
        or restarts the pipeline from scratch.

        Each yielded dict has:
            - `node`: name of the node that just finished (or "start"/"end")
            - `status`: current CarouselStatus value
            - `phase_progress`: the live per-slide/label payload
        The stream terminates with a final `{"node": "end", ...}` event.
        """
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
                        "status": final_project.status.value if final_project else "completed",
                        "phase_progress": final_project.phase_progress if final_project else None,
                    }
                    break
                continue

            yield event
            if event.get("node") in ("end", "error"):
                break

    async def resume_pipeline(self, project_id: UUID) -> CarouselProject:
        """Re-invoke the pipeline against an existing checkpoint thread.

        Used by the `/resume` route after a crash. Idempotent-by-design
        nodes (persist_slides, image_worker, export) short-circuit on
        already-completed work so expensive API calls don't re-fire.

        If no checkpoint exists (e.g. the previous run failed before the
        first node completed), the pipeline starts from scratch.
        """
        if self._checkpointer is None:
            raise RuntimeError(_ERR_NO_CHECKPOINTER)
        project = await self._repo.get_project_by_id(project_id)
        if project is None:
            raise ValueError(_ERR_PROJECT_NOT_FOUND.format(project_id))

        output_dir = self._output_base / str(project_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        graph = build_graph(self._build_deps(), checkpointer=self._checkpointer)
        config = {"configurable": {"thread_id": self._thread_id(project_id)}}

        # Guard against missing checkpoints — a node may have failed before
        # LangGraph wrote the first checkpoint, or the sqlite file may have
        # been deleted. Fall back to a fresh run rather than crash on None.
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
            final_state = await graph.ainvoke(input_state, config=config)
        except Exception as exc:
            project.mark_failed(str(exc))
            await self._repo.update_project(project)
            raise

        final_project: CarouselProject = final_state["project"]
        return final_project

    async def _phase1_research(
        self,
        project: CarouselProject,
        seed_urls: list[str],
    ) -> list[ResearchSource]:
        return await run_research(
            project,
            seed_urls,
            repo=self._repo,
            research_tool=self._research,
        )

    async def _phase2_3_content(
        self,
        project: CarouselProject,
        sources: list[ResearchSource],
    ) -> tuple[list[SlideData], str]:
        return await run_content(
            project,
            sources,
            llm=self._llm,
            template=self._template,
        )

    def _phase4_design(self, project: CarouselProject, slides: list[SlideData]) -> str:
        return run_design(project, slides, template=self._template)

    async def _phase5_images(
        self,
        project: CarouselProject,
        slides: list[SlideData],
        output_dir: Path,
    ) -> None:
        await run_images(
            project,
            slides,
            output_dir,
            repo=self._repo,
            image_registry=self._image_registry,
        )

    async def _phase6_bilingual_export(
        self,
        project: CarouselProject,
        slides_data: list[SlideData],
        pt_html: str,
        output_dir: Path,
    ) -> None:
        await run_bilingual_export(
            project,
            slides_data,
            pt_html,
            output_dir,
            export=self._export,
            pdf_builder=self._pdf_slide_builder,
            template=self._template,
        )

    async def _render_language(
        self,
        project: CarouselProject,
        _slides: list[SlideData],
        language: str,
        html_content: str,
        output_dir: Path,
    ) -> None:
        await render_language(
            project,
            language,
            html_content,
            output_dir,
            export=self._export,
            pdf_builder=self._pdf_slide_builder,
        )

    async def _phase7_caption(self, project: CarouselProject, slides: list[SlideData]) -> str:
        return await run_caption(project, slides, llm=self._llm, template=self._template)

    async def _phase8_linkedin(self, project: CarouselProject) -> None:
        await run_linkedin(project, repo=self._repo, generator=self._linkedin_post_generator)

    def _resolve_theme(self, project: CarouselProject) -> dict[str, str]:
        return resolve_theme(project)

    async def re_render_slides(self, project_id: UUID) -> CarouselProject:
        """Re-render PT (and EN if available) slides + PDFs after edits.

        Used by the agent's `refine_carousel_copy` tool when a slide_*
        target is rewritten. Reads slides from the DB (with their persisted
        extras + translation_en), re-renders both languages when EN
        translations exist, and bumps `project.updated_at` so the
        frontend's cache-busting `?v=` query param picks up the new URLs.
        """
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
        await self._phase6_bilingual_export(project, slides_data, pt_html, Path(project.output_dir))
        project.updated_at = datetime.utcnow()
        return await self._repo.update_project(project)

    async def _set_progress(
        self,
        project: CarouselProject,
        label: str,
        current: int | None = None,
        total: int | None = None,
        detail: str | None = None,
    ) -> CarouselProject:
        return await set_progress(
            project,
            repo=self._repo,
            label=label,
            current=current,
            total=total,
            detail=detail,
        )
