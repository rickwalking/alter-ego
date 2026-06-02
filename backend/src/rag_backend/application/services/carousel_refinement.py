"""Carousel refinement operations: image regeneration and design overrides.

Extracted from the legacy monolith agent to keep the refinement module focused.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from rag_backend.application.services.carousel.nodes.design import OVERRIDES_FILENAME
from rag_backend.application.services.carousel.nodes.images import run_image_one
from rag_backend.application.services.carousel.types import unpack_extras
from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_ERR_PROJECT_NOT_FOUND = "Carousel project {} not found"
_ERR_NO_OUTPUT_DIR_IMAGE = (
    "Carousel project {} has no output_dir; cannot regenerate image."
)
_ERR_SLIDE_NOT_FOUND = "Slide {} not found in project {}"
_ERR_NO_IMAGE_PROMPT = "Slide {} has no image_prompt to refine."
_ERR_EMPTY_IMAGE_PROMPT = "LLM returned an empty image prompt; no changes applied."
_ERR_NO_OUTPUT_DIR_DESIGN = (
    "Carousel project {} has no output_dir; cannot apply design changes."
)
_ERR_NO_SLIDES = "Carousel project {} has no slides."
_ERR_EMPTY_CSS = "LLM returned empty CSS; no changes applied."
_ERR_WRITE_OVERRIDES = "Could not write design overrides to {}: {}"

IMAGE_PROMPT_REWRITE_TEMPLATE = (
    "You are editing an image generation prompt for a social media "
    "carousel slide. Apply the user's instruction to the prompt below. "
    "Return ONLY the rewritten prompt, nothing else.\n\n"
    "Instruction: {instruction}\n\n"
    "Original prompt:\n<<<{current_prompt}>>>"
)

DESIGN_PROMPT_TEMPLATE = (
    "You are a CSS expert editing an Instagram carousel HTML template. "
    "The template uses fixed-size slides (1080x1350px) with inline CSS. "
    "Generate ONLY a raw CSS snippet that applies the user's instruction. "
    "Do NOT use <style> tags. Use existing class names where possible. "
    "Keep the existing design system intact — only override what is needed.\n\n"
    "IMPORTANT class names by slide type:\n"
    "- Intro slide (slide 1): .s1-hero-img for the image\n"
    "- Summary slide (slide 2): .summary-slide, no image\n"
    "- Content slides (slides 3-5): .hero-img for the image\n"
    "- CTA slide (slide 7): no image\n"
    "Use the correct class for the slide mentioned in the instruction.\n\n"
    "Instruction: {instruction}\n\n"
    "Existing CSS classes (relevant excerpts):\n"
    "```css\n"
    "{current_css}"
    "```\n\n"
    "Return ONLY the raw CSS override snippet, nothing else."
)


def _render_image_rewrite_prompt(instruction: str, current_prompt: str) -> str:
    """Render image prompt rewrite via external registry.

    Falls back to inline template if registry is unavailable.
    """
    try:
        from rag_backend.agents.prompts.registry import render_prompt

        prompt_text, _ = render_prompt(
            "refinement",
            "image_rewrite",
            variables={
                "instruction": instruction,
                "current_prompt": current_prompt,
            },
            version="v1",
        )
    except Exception:
        return IMAGE_PROMPT_REWRITE_TEMPLATE.format(
            instruction=instruction, current_prompt=current_prompt
        )
    else:
        return prompt_text


def _render_design_prompt(instruction: str, current_css: str) -> str:
    """Render design CSS prompt via external registry.

    Falls back to inline template if registry is unavailable.
    """
    try:
        from rag_backend.agents.prompts.registry import render_prompt

        prompt_text, _ = render_prompt(
            "refinement",
            "design_css",
            variables={
                "instruction": instruction,
                "current_css": current_css,
            },
            version="v1",
        )
    except Exception:
        return DESIGN_PROMPT_TEMPLATE.format(
            instruction=instruction, current_css=current_css
        )
    else:
        return prompt_text


class CarouselRefinementMixin:
    """Mixin providing carousel refinement operations.

    Expected to be mixed into a class that provides:
        - _repo: CarouselRepository
        - _llm: LLMService
        - _image_registry
        - _phase4_design(project, slides_data) -> str
        - re_render_slides(project_id) -> CarouselProject
    """

    async def regenerate_slide_image(
        self: CarouselRefinementMixin,
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
            raise ValueError(_ERR_PROJECT_NOT_FOUND.format(project_id))
        if not project.output_dir:
            raise ValueError(_ERR_NO_OUTPUT_DIR_IMAGE.format(project_id))

        slides = await self._repo.get_slides_by_project(project_id)
        slide = next((s for s in slides if s.slide_number == slide_number), None)
        if slide is None:
            raise ValueError(_ERR_SLIDE_NOT_FOUND.format(slide_number, project_id))

        slide_data = unpack_extras(slide)
        current_prompt = slide_data.image_prompt or ""
        if not current_prompt:
            raise ValueError(_ERR_NO_IMAGE_PROMPT.format(slide_number))

        rewrite_prompt = _render_image_rewrite_prompt(instruction, current_prompt)
        new_prompt = await self._llm.generate(
            [{"role": "user", "content": rewrite_prompt}],
            temperature=0.7,
        )
        new_prompt = new_prompt.strip()
        if not new_prompt:
            raise ValueError(_ERR_EMPTY_IMAGE_PROMPT)

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
            summary_points=slide_data.summary_points,
            tldr_strip=slide_data.tldr_strip,
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
        self: CarouselRefinementMixin,
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
            raise ValueError(_ERR_PROJECT_NOT_FOUND.format(project_id))
        if not project.output_dir:
            raise ValueError(_ERR_NO_OUTPUT_DIR_DESIGN.format(project_id))

        slides = await self._repo.get_slides_by_project(project_id)
        if not slides:
            raise ValueError(_ERR_NO_SLIDES.format(project_id))

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

        design_prompt = _render_design_prompt(instruction, current_css[:2000])
        override_css = await self._llm.generate(
            [{"role": "user", "content": design_prompt}],
            temperature=0.3,
        )
        override_css = override_css.strip()
        if not override_css:
            raise ValueError(_ERR_EMPTY_CSS)

        # Strip markdown fences if the LLM wrapped the CSS
        if override_css.startswith("```css"):
            override_css = override_css[6:]
        if override_css.startswith("```"):
            override_css = override_css[3:]
        if override_css.endswith("```"):
            override_css = override_css[:-3]
        override_css = override_css.strip()

        output_dir = Path(project.output_dir)
        overrides_path = output_dir / OVERRIDES_FILENAME
        try:
            overrides_path.write_text(override_css, encoding=ENCODING_UTF8)
        except OSError as exc:
            logger.exception("Failed to write design overrides")
            raise ValueError(_ERR_WRITE_OVERRIDES.format(overrides_path, exc)) from exc

        # Re-export with the new overrides baked in
        await self.re_render_slides(project_id)
        return project
