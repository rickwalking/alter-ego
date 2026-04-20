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
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.domain.constants import (
    CAROUSEL_THEMES,
    SLIDE_TYPE_CONTENT,
)
from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
    CarouselTheme,
    ResearchSource,
    ResearchSourceType,
)
from rag_backend.domain.protocols import (
    CarouselExportService,
    CarouselRepository,
    ImageGenerationService,
    LLMService,
    ResearchTool,
)


@dataclass
class SlideData:
    """Structured slide data from content synthesis."""

    slide_number: int
    slide_type: str
    heading: str
    body: str
    image_prompt: str | None = None


class CarouselAgent:
    """Sub-agent specialized in carousel content generation."""

    def __init__(
        self,
        repository: CarouselRepository,
        llm_service: LLMService,
        research_tool: ResearchTool,
        image_service: ImageGenerationService,
        export_service: CarouselExportService,
        output_base_dir: str = "./output/carousels",
    ) -> None:
        self._repo = repository
        self._llm = llm_service
        self._research = research_tool
        self._images = image_service
        self._export = export_service
        self._output_base = Path(output_base_dir)
        self._template = CarouselTemplateBuilder()

    async def execute_pipeline(self, project_id: UUID) -> CarouselProject:
        """Execute the full 7-phase carousel generation pipeline."""
        project = await self._repo.get_project_by_id(project_id)
        if project is None:
            raise ValueError(f"Carousel project {project_id} not found")

        output_dir = self._output_base / str(project_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Phase 1: Research
            project.update_status(CarouselStatus.RESEARCHING)
            project = await self._repo.update_project(project)
            sources = await self._phase1_research(project)

            # Phase 2-3: Content synthesis
            project.update_status(CarouselStatus.DRAFTING)
            project = await self._repo.update_project(project)
            slides_data, blog_markdown = await self._phase2_3_content(
                project, sources
            )

            # Save slides
            for slide_data in slides_data:
                slide = CarouselSlide(
                    project_id=project.id,
                    slide_number=slide_data.slide_number,
                    slide_type=slide_data.slide_type,
                    heading=slide_data.heading,
                    body=slide_data.body,
                    image_prompt=slide_data.image_prompt,
                )
                await self._repo.create_slide(slide)

            if project.blog_markdown is None:
                project.blog_markdown = blog_markdown
            project = await self._repo.update_project(project)

            # Phase 4: Design system
            project.update_status(CarouselStatus.DESIGNING)
            project = await self._repo.update_project(project)
            html_content = self._phase4_design(project, slides_data)
            project = await self._repo.update_project(project)

            # Phase 5: Image generation
            if project.generate_images:
                project.update_status(CarouselStatus.GENERATING_IMAGES)
                project = await self._repo.update_project(project)
                await self._phase5_images(project, slides_data, output_dir)

            # Phase 6: Assembly & Export
            project.update_status(CarouselStatus.EXPORTING)
            project = await self._repo.update_project(project)
            await self._phase6_export(html_content, output_dir)

            # Phase 7: Caption
            caption = await self._phase7_caption(project, slides_data)
            project.caption = caption

            # Complete
            project.mark_completed(str(output_dir))
            project = await self._repo.update_project(project)

        except Exception as exc:
            project.mark_failed(str(exc))
            await self._repo.update_project(project)
            raise

        return project

    async def _phase1_research(
        self, project: CarouselProject
    ) -> list[ResearchSource]:
        """Phase 1: Parallel web research."""
        query = f"{project.topic} {project.niche}"
        search_results = await self._research.search_web(
            query=query,
            source_types=[
                ResearchSourceType.TWITTER,
                ResearchSourceType.BLOG,
                ResearchSourceType.NEWS,
                ResearchSourceType.GITHUB,
            ],
        )

        sources: list[ResearchSource] = []
        for result in search_results[:10]:
            source = ResearchSource(
                project_id=project.id,
                source_url=result.get("url", ""),
                source_type=ResearchSourceType.BLOG,
                title=result.get("title"),
                relevance_score=1.0,
            )
            created = await self._repo.create_research_source(source)
            sources.append(created)

        # Scrape top sources in parallel
        tasks = [self._scrape_source(s) for s in sources[:5]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for source, result in zip(sources[:5], results, strict=False):
            if not isinstance(result, Exception) and isinstance(result, str):
                source.extracted_content = result
                await self._repo.create_research_source(source)

        return sources

    async def _scrape_source(self, source: ResearchSource) -> str:
        """Scrape a single source URL."""
        try:
            content = await self._research.scrape_url(source.source_url)
            source.extracted_content = content
            await self._repo.create_research_source(source)
            return content
        except Exception:
            return ""

    async def _phase2_3_content(
        self,
        project: CarouselProject,
        sources: list[ResearchSource],
    ) -> tuple[list[SlideData], str]:
        """Phases 2-3: Title optimization and bilingual content synthesis."""
        research_context = "\n\n".join(
            f"Source: {s.source_url}\n{s.extracted_content or ''}"
            for s in sources
            if s.extracted_content
        )

        # Phase 2: Title optimization
        title_prompt = self._template.build_title_prompt(project, research_context)
        title_response = await self._llm.generate(
            messages=[{"role": "user", "content": title_prompt}],
            temperature=0.8,
        )

        try:
            title_data = json.loads(title_response)
            project.set_title(
                title=title_data.get("title_pt", title_data.get("title", project.topic)),
                subtitle=title_data.get("subtitle_pt", title_data.get("subtitle")),
            )
        except (json.JSONDecodeError, KeyError):
            project.set_title(title=project.topic)

        # Phase 3: Bilingual content synthesis
        content_prompt = self._template.build_content_prompt(
            project, research_context
        )
        content_response = await self._llm.generate(
            messages=[{"role": "user", "content": content_prompt}],
            temperature=0.7,
        )

        try:
            content_data = json.loads(content_response)
            slides_data: list[SlideData] = []
            for slide_json in content_data.get("slides", []):
                slides_data.append(
                    SlideData(
                        slide_number=slide_json["number"],
                        slide_type=slide_json["type"],
                        heading=slide_json["heading"],
                        body=slide_json["body"],
                        image_prompt=slide_json.get("image_prompt"),
                    )
                )

            blog_pt = content_data.get("blog_pt", content_data.get("blog_markdown", ""))
            blog_en = content_data.get("blog_en", "")

            project.blog_markdown = blog_pt
            if blog_en:
                project.blog_translations = {"pt": blog_pt, "en": blog_en}
            else:
                project.blog_translations = {"pt": blog_pt}

            # Update title/subtitle with bilingual data if available
            if "title_pt" in content_data:
                project.set_title(
                    title=content_data.get("title_pt", project.title or project.topic),
                    subtitle=content_data.get("subtitle_pt", project.subtitle),
                )
        except (json.JSONDecodeError, KeyError):
            slides_data = [
                SlideData(
                    slide_number=1,
                    slide_type="intro",
                    heading=project.title or project.topic,
                    body=project.subtitle or "",
                )
            ]

        return slides_data, project.blog_markdown or ""

    def _phase4_design(
        self, project: CarouselProject, slides: list[SlideData]
    ) -> str:
        """Phase 4: Generate HTML carousel with design system and store design tokens."""
        theme = self._resolve_theme(project)
        project.set_theme_colors(
            primary=theme["primary"],
            accent=theme["accent"],
            background=theme["background"],
        )

        design_tokens = CarouselTemplateBuilder.generate_design_tokens(project)
        project.design_tokens = design_tokens

        slide_dicts = [
            {
                "number": str(s.slide_number),
                "type": s.slide_type,
                "heading": s.heading,
                "body": s.body,
            }
            for s in slides
        ]
        return self._template.build_carousel_html(project, slide_dicts, theme)

    async def _phase5_images(
        self,
        project: CarouselProject,
        slides: list[SlideData],
        output_dir: Path,
    ) -> None:
        """Phase 5: Generate images for content slides."""
        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        content_slides = [
            s for s in slides if s.slide_type == SLIDE_TYPE_CONTENT and s.image_prompt
        ]

        for slide in content_slides:
            image_path = str(images_dir / f"slide_{slide.slide_number}.jpg")
            await self._images.generate_image(
                prompt=slide.image_prompt,
                output_path=image_path,
            )

    async def _phase6_export(self, html_content: str, output_dir: Path) -> list[str]:
        """Phase 6: Export HTML carousel to individual JPG slides."""
        return await self._export.export_slides(
            html_content=html_content,
            output_dir=str(output_dir),
        )

    async def _phase7_caption(
        self, project: CarouselProject, slides: list[SlideData]
    ) -> str:
        """Phase 7: Generate Instagram caption."""
        slide_headings = [(s.slide_number, s.heading) for s in slides]
        caption_prompt = self._template.build_caption_prompt(
            project, slide_headings
        )
        return await self._llm.generate(
            messages=[{"role": "user", "content": caption_prompt}],
            temperature=0.8,
        )

    def _resolve_theme(self, project: CarouselProject) -> dict[str, str]:
        """Resolve color theme for the carousel."""
        if project.theme != CarouselTheme.AUTO:
            return CAROUSEL_THEMES.get(
                project.theme.value, CAROUSEL_THEMES["ai_competition"]
            )
        return CAROUSEL_THEMES["ai_competition"]
