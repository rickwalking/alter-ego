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

from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver

from rag_backend.application.services.carousel.graph import CarouselDeps, build_graph
from rag_backend.application.services.carousel.nodes.caption import run_caption
from rag_backend.application.services.carousel.nodes.content import run_content
from rag_backend.application.services.carousel.nodes.design import resolve_theme, run_design
from rag_backend.application.services.carousel.nodes.export import (
    render_language,
    run_bilingual_export,
)
from rag_backend.application.services.carousel.nodes.images import run_image_one, run_images
from rag_backend.application.services.carousel.nodes.linkedin import run_linkedin
from rag_backend.application.services.carousel.nodes.progress import set_progress
from rag_backend.application.services.carousel.nodes.research import run_research
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.application.services.carousel.types import (
    SlideData,
    unpack_extras,
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
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


class CarouselAgent:
    """Sub-agent specialized in carousel content generation."""

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
        checkpointer: BaseCheckpointSaver[Any] | None = None,
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

    @staticmethod
    def _thread_id(project_id: UUID) -> str:
        """Deterministic thread_id keyed on project_id.

        Calling `/generate` and then `/resume` both use this id, so the
        resume path picks up the same checkpoint thread.
        """
        return f"carousel-{project_id}"

    def _build_deps(self) -> CarouselDeps:
        return CarouselDeps(
            repo=self._repo,
            llm=self._llm,
            research_tool=self._research,
            image_registry=self._image_registry,
            export=self._export,
            template=self._template,
            linkedin_generator=self._linkedin_post_generator,
            pdf_builder=self._pdf_slide_builder,
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
            raise ValueError(f"Carousel project {project_id} not found")

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

    async def stream_pipeline(
        self,
        project_id: UUID,
        seed_urls: list[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Run the pipeline and yield progress events as they happen.

        Each yielded dict has:
            - `node`: name of the node that just finished (or "start"/"end")
            - `status`: current CarouselStatus value
            - `phase_progress`: the live per-slide/label payload
        The stream terminates with a final `{"node": "end", ...}` event.
        Used by the SSE route to drive real-time UI updates without
        polling `/status`.
        """
        project = await self._repo.get_project_by_id(project_id)
        if project is None:
            raise ValueError(f"Carousel project {project_id} not found")

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

        # If a checkpoint exists for this thread, resume from it so an SSE
        # reconnect doesn't restart the pipeline from phase 1.
        has_checkpoint = False
        if config is not None:
            try:
                snapshot = await graph.aget_state(config)
                has_checkpoint = snapshot is not None and bool(snapshot.values)
            except Exception:
                has_checkpoint = False

        yield {
            "node": "start",
            "status": project.status.value,
            "phase_progress": project.phase_progress,
        }

        try:
            stream_input = None if has_checkpoint else initial_state
            async for update in graph.astream(stream_input, config=config):
                # `update` is {node_name: partial_state_dict}. We emit
                # one SSE event per finished node with the latest
                # project snapshot so the frontend can refresh its UI.
                for node_name, partial in update.items():
                    snapshot = partial.get("project") if isinstance(partial, dict) else None
                    if snapshot is None:
                        continue
                    yield {
                        "node": node_name,
                        "status": snapshot.status.value,
                        "phase_progress": snapshot.phase_progress,
                    }
        except Exception as exc:
            # Re-fetch so we capture the phase_progress that was updated
            # inside the LangGraph state (the original `project` is stale).
            latest_project = await self._repo.get_project_by_id(project_id)
            if latest_project is None:
                latest_project = project
            latest_project.mark_failed(str(exc))
            await self._repo.update_project(latest_project)
            yield {
                "node": "error",
                "status": latest_project.status.value,
                "phase_progress": latest_project.phase_progress,
                "error": str(exc),
            }
            return

        final_project = await self._repo.get_project_by_id(project_id)
        yield {
            "node": "end",
            "status": final_project.status.value if final_project else "completed",
            "phase_progress": final_project.phase_progress if final_project else None,
        }

    async def resume_pipeline(self, project_id: UUID) -> CarouselProject:
        """Re-invoke the pipeline against an existing checkpoint thread.

        Used by the `/resume` route after a crash. Idempotent-by-design
        nodes (persist_slides, image_worker, export) short-circuit on
        already-completed work so expensive API calls don't re-fire.
        """
        if self._checkpointer is None:
            raise RuntimeError(
                "resume_pipeline requires a checkpointer; none was injected"
            )
        project = await self._repo.get_project_by_id(project_id)
        if project is None:
            raise ValueError(f"Carousel project {project_id} not found")

        output_dir = self._output_base / str(project_id)
        graph = build_graph(self._build_deps(), checkpointer=self._checkpointer)
        config = {"configurable": {"thread_id": self._thread_id(project_id)}}

        try:
            final_state = await graph.ainvoke(None, config=config)  # resume from checkpoint
        except Exception as exc:
            project.mark_failed(str(exc))
            await self._repo.update_project(project)
            raise

        final_project: CarouselProject = final_state["project"]
        _ = output_dir  # output_dir is baked into the checkpointed state
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
        slides: list[SlideData],
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
        await run_linkedin(
            project, repo=self._repo, generator=self._linkedin_post_generator
        )

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
            raise ValueError(f"Carousel project {project_id} not found")
        if not project.output_dir:
            raise ValueError(
                f"Carousel project {project_id} has no output_dir; cannot re-render slides."
            )
        slides = await self._repo.get_slides_by_project(project_id)
        if not slides:
            raise ValueError(f"Carousel project {project_id} has no slides.")

        slides_data = [unpack_extras(s) for s in slides]
        pt_html = self._phase4_design(project, slides_data)
        await self._phase6_bilingual_export(project, slides_data, pt_html, Path(project.output_dir))
        project.updated_at = datetime.utcnow()
        return await self._repo.update_project(project)

    async def regenerate_slide_image(
        self,
        project_id: UUID,
        slide_number: int,
        instruction: str,
    ) -> CarouselProject:
        """Regenerate the hero image for a single slide.

        Rewrites the slide's `image_prompt` via LLM using *instruction*,
        generates a new image via the project's configured provider, and
        re-exports the slide JPGs + PDF so the user sees the update.
        """
        project = await self._repo.get_project_by_id(project_id)
        if project is None:
            raise ValueError(f"Carousel project {project_id} not found")
        if not project.output_dir:
            raise ValueError(
                f"Carousel project {project_id} has no output_dir; cannot regenerate image."
            )

        slides = await self._repo.get_slides_by_project(project_id)
        slide = next((s for s in slides if s.slide_number == slide_number), None)
        if slide is None:
            raise ValueError(
                f"Slide {slide_number} not found in project {project_id}"
            )

        slide_data = unpack_extras(slide)
        current_prompt = slide_data.image_prompt or ""
        if not current_prompt:
            raise ValueError(
                f"Slide {slide_number} has no image_prompt to refine."
            )

        rewrite_prompt = (
            "You are editing an image generation prompt for a social media "
            "carousel slide. Apply the user's instruction to the prompt below. "
            "Return ONLY the rewritten prompt, nothing else.\n\n"
            f"Instruction: {instruction}\n\n"
            f"Original prompt:\n<<<{current_prompt}>>>"
        )
        new_prompt = await self._llm.generate(
            [{"role": "user", "content": rewrite_prompt}],
            temperature=0.7,
        )
        new_prompt = new_prompt.strip()
        if not new_prompt:
            raise ValueError("LLM returned an empty image prompt; no changes applied.")

        # Persist the new prompt on both the column and in extras for safety
        slide.image_prompt = new_prompt
        extras: dict[str, object] = dict(slide.extras or {})
        extras["image_prompt"] = new_prompt
        slide.extras = extras
        await self._repo.update_slide(slide)

        # Update the in-memory SlideData so image generation uses the new prompt
        slide_data = slide_data.__class__(
            slide_number=slide_data.slide_number,
            slide_type=slide_data.slide_type,
            heading=slide_data.heading,
            body=slide_data.body,
            image_prompt=new_prompt,
            features=slide_data.features,
            stats=slide_data.stats,
            insight=slide_data.insight,
            translation_en=slide_data.translation_en,
        )

        # Regenerate the image file
        output_dir = Path(project.output_dir)
        await run_image_one(
            project,
            slide_data,
            output_dir,
            image_registry=self._image_registry,
        )

        # Re-export HTML + PDF so the new image is baked in
        await self.re_render_slides(project_id)
        return project

    async def refine_carousel_design(
        self,
        project_id: UUID,
        instruction: str,
    ) -> CarouselProject:
        """Apply a CSS/layout design change to the carousel.

        Uses the LLM to translate a natural-language design request into
        CSS overrides, writes them to the project's output directory as
        `design_overrides.css`, and re-exports the slide JPGs + PDF.
        Does NOT regenerate source images.
        """
        project = await self._repo.get_project_by_id(project_id)
        if project is None:
            raise ValueError(f"Carousel project {project_id} not found")
        if not project.output_dir:
            raise ValueError(
                f"Carousel project {project_id} has no output_dir; cannot apply design changes."
            )

        slides = await self._repo.get_slides_by_project(project_id)
        if not slides:
            raise ValueError(f"Carousel project {project_id} has no slides.")

        # Build current HTML so the LLM can see the existing CSS classes
        slides_data = [unpack_extras(s) for s in slides]
        current_html = self._phase4_design(project, slides_data)

        # Extract the CSS block from the HTML for the LLM
        css_start = current_html.find("<style>")
        css_end = current_html.find("</style>")
        current_css = (
            current_html[css_start + 7 : css_end].strip()
            if css_start != -1 and css_end != -1
            else ""
        )

        design_prompt = (
            "You are a CSS expert editing an Instagram carousel HTML template. "
            "The template uses fixed-size slides (1080x1350px) with inline CSS. "
            "Generate ONLY a raw CSS snippet that applies the user's instruction. "
            "Do NOT use <style> tags. Use existing class names where possible. "
            "Keep the existing design system intact — only override what is needed.\n\n"
            f"Instruction: {instruction}\n\n"
            "Existing CSS classes (relevant excerpts):\n"
            "```css\n"
            f"{current_css[:2000]}\n"
            "```\n\n"
            "Return ONLY the CSS override snippet, nothing else."
        )
        override_css = await self._llm.generate(
            [{"role": "user", "content": design_prompt}],
            temperature=0.3,
        )
        override_css = override_css.strip()
        if not override_css:
            raise ValueError("LLM returned empty CSS; no changes applied.")

        # Strip markdown fences if the LLM wrapped the CSS
        if override_css.startswith("```css"):
            override_css = override_css[5:]
        if override_css.startswith("```"):
            override_css = override_css[3:]
        if override_css.endswith("```"):
            override_css = override_css[:-3]
        override_css = override_css.strip()

        output_dir = Path(project.output_dir)
        overrides_path = output_dir / "design_overrides.css"
        overrides_path.write_text(override_css, encoding="utf-8")

        # Re-export with the new overrides baked in
        await self.re_render_slides(project_id)
        return project

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


