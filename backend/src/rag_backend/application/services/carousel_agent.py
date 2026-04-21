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
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.domain.constants import (
    CAROUSEL_THEMES,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_INTRO,
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
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _build_gemini_prompt(scene: str, theme: dict[str, str]) -> str:
    """Wrap an LLM-provided scene description with mandatory style directives.

    The LLM only controls WHAT is depicted. The HOW (style, palette, ratio,
    no-text rule, concrete tech-scene vocabulary) is enforced by this
    template so generated images match the carousel design system.
    """
    return (
        "Comic/manga style illustration, cyberpunk/sci-fi tech aesthetic, "
        "bold outlines, detailed crosshatching shading, dynamic composition. "
        "Wide panoramic 3:1 ratio. "
        "STRICT: no text, no words, no letters, no labels, no speech bubbles, "
        "no signs, no captions, no code readable as text — purely visual. "
        f"Dark background ({theme['background']}) with {theme['primary']} "
        f"and {theme['accent']} neon glow accents, subtle radial light bloom. "
        "Concrete tech scene only — acceptable elements: monitors, terminals, "
        "code streams as abstract glowing glyphs, holographic UI panels, "
        "circuit boards, neon cityscapes, robots, hooded figures, servers, "
        "data pipelines, abstract geometric networks. "
        "No traditional/dojo/warm-lighting/black-and-white/grid-panel layouts. "
        f"Scene: {scene.strip()}"
    )


def _classify_source(url: str) -> ResearchSourceType:
    """Infer a `ResearchSourceType` from the URL host."""
    lowered = url.lower()
    if "twitter.com" in lowered or "x.com" in lowered:
        return ResearchSourceType.TWITTER
    if "github.com" in lowered:
        return ResearchSourceType.GITHUB
    return ResearchSourceType.BLOG


def _extract_json(raw: str) -> Any:
    """Parse JSON from an LLM response, tolerating markdown code fences
    and leading/trailing prose. Raises json.JSONDecodeError on failure.
    """
    candidate = raw.strip()
    fence_match = _JSON_FENCE_RE.search(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()
    else:
        # Fallback: take the substring from the first '{' to the last '}'.
        first = candidate.find("{")
        last = candidate.rfind("}")
        if first != -1 and last != -1 and last > first:
            candidate = candidate[first : last + 1]
    return json.loads(candidate)


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

    async def execute_pipeline(
        self,
        project_id: UUID,
        seed_urls: list[str] | None = None,
    ) -> CarouselProject:
        """Execute the full 7-phase carousel generation pipeline.

        Args:
            project_id: Carousel project to run the pipeline for.
            seed_urls: Primary sources the user provided (tweets, blog posts,
                official docs). These are scraped first and bias the content
                synthesis; DDG search only supplements them.
        """
        project = await self._repo.get_project_by_id(project_id)
        if project is None:
            raise ValueError(f"Carousel project {project_id} not found")

        output_dir = self._output_base / str(project_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Phase 1: Research
            project.update_status(CarouselStatus.RESEARCHING)
            project = await self._repo.update_project(project)
            sources = await self._phase1_research(project, seed_urls or [])

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
        self,
        project: CarouselProject,
        seed_urls: list[str],
    ) -> list[ResearchSource]:
        """Phase 1: research.

        User-provided `seed_urls` (the original tweet, blog post, etc.) are
        the authoritative primary sources — they go first and get scraped
        before anything else. DDG search only supplements them up to 10
        sources total, so the carousel content stays anchored to the user's
        actual context instead of drifting toward whatever DDG surfaces for
        the topic string.
        """
        sources: list[ResearchSource] = [
            ResearchSource(
                project_id=project.id,
                source_url=url,
                source_type=_classify_source(url),
                title=None,
                relevance_score=2.0,
            )
            for url in seed_urls
            if url
        ]

        if len(sources) < 10:
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
            existing = {s.source_url for s in sources}
            remaining = 10 - len(sources)
            for r in search_results:
                url = r.get("url", "")
                if url and url not in existing:
                    sources.append(
                        ResearchSource(
                            project_id=project.id,
                            source_url=url,
                            source_type=ResearchSourceType.BLOG,
                            title=r.get("title"),
                            relevance_score=1.0,
                        )
                    )
                    existing.add(url)
                    if len(sources) - len(seed_urls) >= remaining:
                        break

        # Scrape top sources in parallel, attach content in memory —
        # persisting each twice would violate the UNIQUE constraint on id.
        scrape_tasks = [self._scrape_source(s.source_url) for s in sources[:5]]
        scrape_results = await asyncio.gather(
            *scrape_tasks, return_exceptions=True
        )
        for source, result in zip(sources[:5], scrape_results, strict=False):
            if isinstance(result, str) and result:
                source.extracted_content = result

        persisted: list[ResearchSource] = []
        for source in sources:
            persisted.append(await self._repo.create_research_source(source))
        return persisted

    async def _scrape_source(self, url: str) -> str:
        """Scrape a single URL. Returns content or empty string on failure."""
        try:
            return await self._research.scrape_url(url)
        except Exception as exc:
            logger.warning("carousel_scrape_failed", url=url, error=str(exc))
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
            title_data = _extract_json(title_response)
            project.set_title(
                title=title_data.get("title_pt", title_data.get("title", project.topic)),
                subtitle=title_data.get("subtitle_pt", title_data.get("subtitle")),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning(
                "carousel_title_json_parse_failed",
                project_id=str(project.id),
                error=str(exc),
                raw_response=title_response[:2000],
            )
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
            content_data = _extract_json(content_response)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.error(
                "carousel_content_json_parse_failed",
                project_id=str(project.id),
                error=str(exc),
                raw_response=content_response[:4000],
            )
            raise ValueError(
                "Content synthesis returned non-JSON output; cannot continue."
            ) from exc

        try:
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
        except (KeyError, TypeError) as exc:
            logger.error(
                "carousel_slide_shape_invalid",
                project_id=str(project.id),
                error=str(exc),
                content_keys=list(content_data.keys()) if isinstance(content_data, dict) else None,
            )
            raise ValueError("Content synthesis returned slides with missing fields.") from exc

        if not slides_data:
            logger.error(
                "carousel_no_slides_produced",
                project_id=str(project.id),
                content_keys=list(content_data.keys()),
            )
            raise ValueError("Content synthesis returned zero slides.")

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
        """Phase 5: Generate images for content slides.

        The LLM's `image_prompt` is treated as a scene *description* only —
        it frequently ignores style rules (asks for speech bubbles, dojo
        scenes, grid layouts, warm lighting). We wrap it here with the
        mandatory cyberpunk/sci-fi directives and the project's palette so
        every generated image matches the carousel design system.
        """
        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        theme = self._resolve_theme(project)

        # Per the original skill: intro + content slides get images;
        # closing (checklist) and cta (share-buttons) slides don't.
        image_types = {SLIDE_TYPE_INTRO, SLIDE_TYPE_CONTENT}
        slides_with_images = [
            s for s in slides if s.slide_type in image_types and s.image_prompt
        ]

        for slide in slides_with_images:
            image_path = str(images_dir / f"slide_{slide.slide_number}.jpg")
            final_prompt = _build_gemini_prompt(slide.image_prompt or "", theme)
            await self._images.generate_image(
                prompt=final_prompt,
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
