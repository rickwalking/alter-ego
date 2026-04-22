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
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.application.services.linkedin_post_generator import (
    LinkedInPostGenerator,
)
from rag_backend.application.services.pdf_slide_builder import PdfSlideBuilder
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
    LLMService,
    ResearchTool,
)
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

# Hard cap on closing/content slide feature cards. The .feature-grid CSS
# is tuned for 2-4 items; 5+ overflow past the slide footer.
_MAX_FEATURE_ITEMS = 4


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
    # Structured checklist items for closing/feature slides. Each item is
    # `{"icon": "📝", "title": "...", "body": "..."}`. None for plain-prose
    # slides (intro, CTA, most content slides).
    features: list[dict[str, str]] | None = None
    # Big-number stat cards rendered as a 3-column grid. Each item is
    # `{"value": "80.2%", "label": "SWE-Bench Verified", "detail": "(era 68.9%)"}`.
    stats: list[dict[str, str]] | None = None
    # A single quoted insight with attribution rendered as an accent-
    # bordered card. Shape: `{"quote": "...", "attribution": "..."}`.
    insight: dict[str, str] | None = None
    # Parallel EN counterpart to (heading, body, features, stats, insight)
    # for bilingual rendering. None = no translation provided; we fall
    # back to PT when rendering EN slides.
    translation_en: dict[str, object] | None = None


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
            project = await self._set_progress(project, label="Searching the web for sources")
            sources = await self._phase1_research(project, seed_urls or [])

            # Phase 2-3: Content synthesis
            project.update_status(CarouselStatus.DRAFTING)
            project = await self._set_progress(
                project,
                label="Drafting bilingual slide content",
            )
            slides_data, blog_markdown = await self._phase2_3_content(project, sources)

            # Save slides — persist features/stats/insight into `extras`
            # so the refine flow can re-render this slide later.
            for slide_data in slides_data:
                slide = CarouselSlide(
                    project_id=project.id,
                    slide_number=slide_data.slide_number,
                    slide_type=slide_data.slide_type,
                    heading=slide_data.heading,
                    body=slide_data.body,
                    image_prompt=slide_data.image_prompt,
                    extras=_pack_extras(slide_data),
                )
                await self._repo.create_slide(slide)

            if project.blog_markdown is None:
                project.blog_markdown = blog_markdown
            project = await self._repo.update_project(project)

            # Phase 4: Design system (PT base; EN re-renders below).
            project.update_status(CarouselStatus.DESIGNING)
            project = await self._set_progress(project, label="Resolving theme and design tokens")
            pt_html = self._phase4_design(project, slides_data)
            project = await self._repo.update_project(project)

            # Phase 5: Image generation (language-agnostic — heroes shared)
            if project.generate_images:
                project.update_status(CarouselStatus.GENERATING_IMAGES)
                project = await self._repo.update_project(project)
                await self._phase5_images(project, slides_data, output_dir)

            # Phase 6: Bilingual assembly & export.
            project.update_status(CarouselStatus.EXPORTING)
            project = await self._set_progress(project, label="Rendering PT + EN slide HTML to JPG")
            await self._phase6_bilingual_export(project, slides_data, pt_html, output_dir)

            # Phase 7: Caption
            caption = await self._phase7_caption(project, slides_data)
            project.caption = caption

            # Phase 8: LinkedIn posts (PT + EN, voice-cloned)
            await self._phase8_linkedin(project)

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
        scrape_results = await asyncio.gather(*scrape_tasks, return_exceptions=True)
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
        content_prompt = self._template.build_content_prompt(project, research_context)
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
                raw_features = slide_json.get("features")
                features: list[dict[str, str]] | None = None
                if isinstance(raw_features, list) and raw_features:
                    # Defensive cap: the template's .feature-grid overflows
                    # past 4 items. Even if the LLM ignores the prompt cap,
                    # we truncate here so the rendered JPG never overflows.
                    features = [
                        {
                            "icon": str(item.get("icon") or "✅"),
                            "title": str(item.get("title") or ""),
                            "body": str(item.get("body") or ""),
                        }
                        for item in raw_features[:_MAX_FEATURE_ITEMS]
                        if isinstance(item, dict)
                    ]
                raw_stats = slide_json.get("stats")
                stats: list[dict[str, str]] | None = None
                if isinstance(raw_stats, list) and raw_stats:
                    stats = [
                        {
                            "value": str(item.get("value") or ""),
                            "label": str(item.get("label") or ""),
                            "detail": str(item.get("detail") or ""),
                        }
                        for item in raw_stats
                        if isinstance(item, dict)
                    ]
                raw_insight = slide_json.get("insight")
                insight: dict[str, str] | None = None
                if isinstance(raw_insight, dict) and raw_insight.get("quote"):
                    insight = {
                        "quote": str(raw_insight.get("quote") or ""),
                        "attribution": str(raw_insight.get("attribution") or ""),
                    }
                slides_data.append(
                    SlideData(
                        slide_number=slide_json["number"],
                        slide_type=slide_json["type"],
                        heading=slide_json["heading"],
                        body=slide_json["body"],
                        image_prompt=slide_json.get("image_prompt"),
                        features=features,
                        stats=stats,
                        insight=insight,
                    )
                )

            # Fold the optional EN slide array onto each PT slide by number.
            slides_en_by_number = _build_slides_en_index(content_data.get("slides_en"))
            for sd in slides_data:
                en = slides_en_by_number.get(sd.slide_number)
                if en is not None:
                    sd.translation_en = en
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

    def _phase4_design(self, project: CarouselProject, slides: list[SlideData]) -> str:
        """Phase 4: Generate HTML carousel with design system and store design tokens."""
        theme = self._resolve_theme(project)
        project.set_theme_colors(
            primary=theme["primary"],
            accent=theme["accent"],
            background=theme["background"],
        )

        design_tokens = CarouselTemplateBuilder.generate_design_tokens(project)
        project.design_tokens = design_tokens

        slide_dicts: list[dict[str, Any]] = [
            {
                "number": str(s.slide_number),
                "type": s.slide_type,
                "heading": s.heading,
                "body": s.body,
                "features": s.features,
                "stats": s.stats,
                "insight": s.insight,
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
        scenes, grid layouts, warm lighting). We resolve the project's
        `(image_model, image_style)` pair through the registry to pick
        the vendor SDK + style wrapper, then let the strategy prepend the
        directives and palette to the scene. This is the DIP seam: the
        agent doesn't know which vendor it's calling.
        """
        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        theme = self._resolve_theme(project)
        provider = self._image_registry.resolve(project.image_model, project.image_style)

        # Per the original skill: intro + content slides get images;
        # closing (checklist) and cta (share-buttons) slides don't.
        image_types = {SLIDE_TYPE_INTRO, SLIDE_TYPE_CONTENT}
        slides_with_images = [s for s in slides if s.slide_type in image_types and s.image_prompt]
        total = len(slides_with_images)
        style_label = _style_display_name(project.image_model, project.image_style)

        # Per-slide status array drives the UI checklist. Each task mutates
        # its own slot; a single lock serializes DB writes so concurrent
        # updates don't race.
        slide_status: list[dict[str, str | int]] = [
            {
                "number": s.slide_number,
                "status": "pending",
                "style": style_label,
                "scene": _short_scene(s.image_prompt or ""),
            }
            for s in slides_with_images
        ]
        done_count = 0
        progress_lock = asyncio.Lock()

        async def _publish_progress() -> None:
            nonlocal project
            async with progress_lock:
                project.phase_progress = {
                    "phase": project.status.value,
                    "label": f"Generating {total} slide images in parallel — {style_label}",
                    "current": done_count,
                    "total": total,
                    "slides": [dict(s) for s in slide_status],
                }
                project = await self._repo.update_project(project)

        async def _run_one(index: int, slide: SlideData) -> None:
            nonlocal done_count
            slide_status[index]["status"] = "in_flight"
            await _publish_progress()
            image_path = str(images_dir / f"slide_{slide.slide_number}.jpg")
            final_prompt = provider.strategy.wrap(slide.image_prompt or "", theme)
            try:
                await provider.service.generate_image(
                    prompt=final_prompt,
                    output_path=image_path,
                )
            except Exception:
                slide_status[index]["status"] = "failed"
                await _publish_progress()
                raise
            slide_status[index]["status"] = "done"
            done_count += 1
            await _publish_progress()

        await _publish_progress()  # initial all-pending snapshot
        await asyncio.gather(*[_run_one(i, s) for i, s in enumerate(slides_with_images)])

    async def _phase6_export(self, html_content: str, output_dir: Path) -> list[str]:
        """Phase 6: Export HTML carousel to individual JPG slides."""
        return await self._export.export_slides(
            html_content=html_content,
            output_dir=str(output_dir),
        )

    async def _phase6_bilingual_export(
        self,
        project: CarouselProject,
        slides_data: list[SlideData],
        pt_html: str,
        output_dir: Path,
    ) -> None:
        """Render PT and EN slide JPGs + PDFs into per-language sub-dirs.

        EN slides are rendered only when at least one slide carries a
        `translation_en` payload. Hero images live one directory up
        (`output/<id>/images/slide_N.jpg`) so both languages share them.
        Each language gets its own `slide_*.jpg` outputs and PDF.
        """
        await self._render_language(project, slides_data, "pt", pt_html, output_dir)

        en_available = any(s.translation_en for s in slides_data)
        if not en_available:
            return

        en_slides = _slides_data_for_language(slides_data, "en")
        en_html = self._phase4_design(project, en_slides)
        await self._render_language(project, en_slides, "en", en_html, output_dir)

    async def _render_language(
        self,
        project: CarouselProject,
        slides: list[SlideData],
        language: str,
        html_content: str,
        output_dir: Path,
    ) -> None:
        """Export a single language's slide JPGs + PDF into <output>/<lang>/.

        Hero images live one level up at `<output>/images/slide_N.jpg`,
        so we rewrite the template's `src="images/...` to `src="../images/...`
        before handing it to Playwright.
        """
        lang_dir = output_dir / language
        lang_dir.mkdir(parents=True, exist_ok=True)
        rewritten_html = html_content.replace('src="images/', 'src="../images/')
        slide_paths = await self._export.export_slides(
            html_content=rewritten_html,
            output_dir=str(lang_dir),
        )
        if self._pdf_slide_builder is None or not slide_paths:
            return
        try:
            pdf_path = self._pdf_slide_builder.build(
                slide_paths=slide_paths,
                output_dir=str(lang_dir),
            )
        except (ValueError, FileNotFoundError, OSError) as exc:
            logger.warning(
                "carousel_pdf_build_failed",
                project_id=str(project.id),
                language=language,
                error=str(exc),
            )
            return
        if language == "en":
            project.pdf_path_en = pdf_path
        else:
            project.pdf_path = pdf_path

    async def _phase7_caption(self, project: CarouselProject, slides: list[SlideData]) -> str:
        """Phase 7: Generate Instagram caption."""
        slide_headings = [(s.slide_number, s.heading) for s in slides]
        caption_prompt = self._template.build_caption_prompt(project, slide_headings)
        return await self._llm.generate(
            messages=[{"role": "user", "content": caption_prompt}],
            temperature=0.8,
        )

    async def _phase8_linkedin(self, project: CarouselProject) -> None:
        """Phase 8: Voice-cloned LinkedIn posts in PT and EN.

        Generator is optional — older callers that didn't wire it get no
        LinkedIn posts, and the pipeline still completes.
        """
        if self._linkedin_post_generator is None:
            return
        await self._set_progress(project, label="Writing LinkedIn post (PT + EN)")
        pt, en = await self._linkedin_post_generator.generate_both(project)
        if pt is not None:
            project.linkedin_post_pt = pt.text
        if en is not None:
            project.linkedin_post_en = en.text

    def _resolve_theme(self, project: CarouselProject) -> dict[str, str]:
        """Resolve color theme for the carousel."""
        if project.theme != CarouselTheme.AUTO:
            return CAROUSEL_THEMES.get(project.theme.value, CAROUSEL_THEMES["ai_competition"])
        return CAROUSEL_THEMES["ai_competition"]

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

        slides_data = [_unpack_extras(s) for s in slides]
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
        """Persist a fine-grained progress payload on the project.

        The frontend polls /status which now returns this dict, so the UI
        can show 'Generating slide 3/6 — OpenAI Hyperreal' instead of just
        'generating_images'. Empty current/total is fine for one-shot phases.
        """
        payload: dict[str, str | int] = {
            "phase": project.status.value,
            "label": label,
        }
        if current is not None:
            payload["current"] = current
        if total is not None:
            payload["total"] = total
        if detail:
            payload["detail"] = detail
        project.phase_progress = payload
        return await self._repo.update_project(project)


_IMAGE_PRESET_DISPLAY: dict[tuple[str, str], str] = {
    ("gemini", "comic_neon"): "Gemini Comic Neon",
    ("openai", "cinematic"): "OpenAI Cinematic Photoreal",
    ("openai", "hyperreal"): "OpenAI Hyperreal Graphic Novel",
    ("openai", "neo_anime"): "OpenAI Neo-Anime",
}


def _style_display_name(model: str, style: str) -> str:
    """Render the (model, style) tuple as a human-readable preset name."""
    return _IMAGE_PRESET_DISPLAY.get((model, style), f"{model}/{style}")


def _short_scene(scene: str, max_chars: int = 80) -> str:
    """Trim a scene description to the first max_chars chars on a word boundary."""
    cleaned = scene.strip().replace("\n", " ")
    if len(cleaned) <= max_chars:
        return cleaned
    cut = cleaned[:max_chars].rsplit(" ", 1)[0]
    return cut + "…"


# Fields copied from SlideData into the persisted `extras` JSON. Listed
# here so `_pack_extras` stays a one-liner loop instead of four branches.
_EXTRAS_FIELDS: tuple[str, ...] = (
    "features",
    "stats",
    "insight",
    "image_prompt",
    "translation_en",
)


def _pack_extras(slide_data: SlideData) -> dict[str, object] | None:
    """Bundle features/stats/insight + EN translation into a JSON dict."""
    payload: dict[str, object] = {
        field: value for field in _EXTRAS_FIELDS if (value := getattr(slide_data, field))
    }
    return payload or None


def _build_slides_en_index(
    raw: object,
) -> dict[int, dict[str, object]]:
    """Index the optional `slides_en` array by slide number for fast lookup.

    Tolerates the field being absent or malformed (LLM may skip it).
    Each EN slide carries: heading, body, features?, stats?, insight?
    """
    result: dict[int, dict[str, object]] = {}
    if not isinstance(raw, list):
        return result
    for item in raw:
        if not isinstance(item, dict):
            continue
        number = item.get("number")
        if not isinstance(number, int):
            continue
        result[number] = {
            "heading": str(item.get("heading") or ""),
            "body": str(item.get("body") or ""),
            "features": item.get("features"),
            "stats": item.get("stats"),
            "insight": item.get("insight"),
        }
    return result


def _unpack_extras(slide: CarouselSlide) -> SlideData:
    """Hydrate a SlideData from a persisted CarouselSlide.

    Used by the refine re-render path so the new HTML carries the same
    structured cards (features/stats/insight) as the original render.
    """
    extras = slide.extras or {}
    features = extras.get("features") if isinstance(extras, dict) else None
    stats = extras.get("stats") if isinstance(extras, dict) else None
    insight = extras.get("insight") if isinstance(extras, dict) else None
    translation_en = extras.get("translation_en") if isinstance(extras, dict) else None
    image_prompt = slide.image_prompt or (
        extras.get("image_prompt") if isinstance(extras, dict) else None
    )
    return SlideData(
        slide_number=slide.slide_number,
        slide_type=slide.slide_type,
        heading=slide.heading,
        body=slide.body,
        image_prompt=image_prompt if isinstance(image_prompt, str) else None,
        features=features if isinstance(features, list) else None,
        stats=stats if isinstance(stats, list) else None,
        insight=insight if isinstance(insight, dict) else None,
        translation_en=(translation_en if isinstance(translation_en, dict) else None),
    )


def _slides_data_for_language(slides: list[SlideData], language: str) -> list[SlideData]:
    """Return a copy of slides with text overridden to the target language.

    For 'pt' we return the originals untouched. For 'en' we swap heading,
    body, features, stats, insight from `translation_en` when present.
    """
    if language == "pt":
        return slides

    swapped: list[SlideData] = []
    for sd in slides:
        en = sd.translation_en
        if not en:
            swapped.append(sd)
            continue
        en_features = en.get("features") if isinstance(en, dict) else None
        en_stats = en.get("stats") if isinstance(en, dict) else None
        en_insight = en.get("insight") if isinstance(en, dict) else None
        swapped.append(
            SlideData(
                slide_number=sd.slide_number,
                slide_type=sd.slide_type,
                heading=str(en.get("heading") or sd.heading),
                body=str(en.get("body") or sd.body),
                image_prompt=sd.image_prompt,
                features=en_features if isinstance(en_features, list) else sd.features,
                stats=en_stats if isinstance(en_stats, list) else sd.stats,
                insight=en_insight if isinstance(en_insight, dict) else sd.insight,
                translation_en=sd.translation_en,
            )
        )
    return swapped
