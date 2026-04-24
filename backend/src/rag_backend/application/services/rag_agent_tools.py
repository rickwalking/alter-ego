"""RAG agent carousel tool definitions.

Extracted from rag_agent.py to keep the main agent class under 400 lines.
Each tool is a factory function that closes over the runtime dependencies
(llm, carousel_repository, carousel_agent) and returns a @tool-decorated
function for the Deep Agent framework.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from langchain_core.tools import BaseTool, tool

from rag_backend.domain.models import CarouselProject, CarouselSlide
from rag_backend.domain.protocols import CarouselAgent, CarouselRepository

MIN_TARGET_PARTS = 2
MAX_TARGET_PARTS = 3

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _resolve_refine_target(  # noqa: C901,PLR0911 — dispatcher with early returns
    project: CarouselProject,
    target: str,
    repository: CarouselRepository,
) -> tuple[str | None, Callable[[str], Awaitable[None]]]:
    """Return (current_text, async_setter) for the refine target.

    Keeps the branching out of the tool closure so the set of supported
    targets is easy to extend without bloating the tool function.
    """
    if target == "instagram_caption":

        async def _set_caption(new_text: str) -> None:
            project.caption = new_text
            await repository.update_project(project)

        return project.caption, _set_caption

    if target == "linkedin_post_pt":

        async def _set_pt(new_text: str) -> None:
            project.linkedin_post_pt = new_text
            await repository.update_project(project)

        return project.linkedin_post_pt, _set_pt

    if target == "linkedin_post_en":

        async def _set_en(new_text: str) -> None:
            project.linkedin_post_en = new_text
            await repository.update_project(project)

        return project.linkedin_post_en, _set_en

    async def _noop(_: str) -> None:
        return None

    if target.startswith("slide_heading:") or target.startswith("slide_body:"):
        parts = target.split(":")
        field = parts[0]
        if len(parts) < MIN_TARGET_PARTS:
            return None, _noop
        try:
            slide_number = int(parts[1])
        except ValueError:
            return None, _noop
        language = parts[2] if len(parts) >= MAX_TARGET_PARTS else "pt"
        if language not in {"pt", "en"}:
            return None, _noop

        slides = await repository.get_slides_by_project(project.id)
        slide = next((s for s in slides if s.slide_number == slide_number), None)
        if slide is None:
            return None, _noop

        current = _read_slide_field(slide, field, language)

        async def _update_slide(new_text: str) -> None:
            _write_slide_field(slide, field, language, new_text)
            await repository.update_slide(slide)

        return current, _update_slide

    return None, _noop


def _read_slide_field(slide: CarouselSlide, field: str, language: str) -> str:
    """Read heading/body for the requested language, falling back to PT."""
    if language == "en":
        translation = (slide.extras or {}).get("translation_en") if slide.extras else None
        if isinstance(translation, dict):
            value = translation.get("heading" if field == "slide_heading" else "body")
            if isinstance(value, str) and value:
                return value
    return slide.heading if field == "slide_heading" else slide.body


def _write_slide_field(slide: CarouselSlide, field: str, language: str, new_text: str) -> None:
    """Mutate heading/body in place for the target language."""
    if language == "en":
        extras: dict[str, object] = dict(slide.extras or {})
        translation = extras.get("translation_en")
        if not isinstance(translation, dict):
            translation = {}
        translation = dict(translation)
        translation["heading" if field == "slide_heading" else "body"] = new_text
        extras["translation_en"] = translation
        slide.extras = extras
        return
    if field == "slide_heading":
        slide.heading = new_text
    else:
        slide.body = new_text


# ---------------------------------------------------------------------------
# Tool factories
# ---------------------------------------------------------------------------


def build_refine_carousel_copy_tool(
    llm: object,
    carousel_repository: CarouselRepository,
    carousel_agent: CarouselAgent,
) -> BaseTool:
    """Return the refine_carousel_copy tool closure."""

    @tool
    async def refine_carousel_copy(
        project_id: str,
        target: str,
        instruction: str,
    ) -> str:
        """Rewrite a specific piece of copy on an existing carousel project.

        Use when the user asks to tweak the Instagram caption, LinkedIn
        post (PT or EN), a slide heading, or a slide body on a carousel
        they already generated. This tool edits TEXT only — it does NOT
        regenerate images. For image changes, use regenerate_slide_image.

        Args:
            project_id: UUID of the carousel project to edit.
            target: Which field to rewrite. One of:
                - "instagram_caption"
                - "linkedin_post_pt"
                - "linkedin_post_en"
                - "slide_heading:N" or "slide_heading:N:pt|en"
                - "slide_body:N" or "slide_body:N:pt|en"
                Bare slide_heading:N / slide_body:N defaults to PT.
            instruction: Natural-language edit request from the user
                (e.g. "make it shorter", "swap the hashtags for tech ones",
                "less corporate").
        """
        from uuid import UUID as _UUID

        try:
            project_uuid = _UUID(project_id)
        except ValueError:
            return f"Invalid project_id {project_id!r} — expected a UUID."

        project = await carousel_repository.get_project_by_id(project_uuid)
        if project is None:
            return f"Carousel project {project_id} not found."

        original, apply_update = await _resolve_refine_target(project, target, carousel_repository)
        if original is None:
            return f"Cannot refine {target!r}: field is empty or target selector is unknown."

        from rag_backend.agents.prompts.registry import render_prompt

        rewrite_prompt, _ = render_prompt(
            "refinement",
            "copy_rewrite",
            variables={
                "instruction": instruction,
                "original_text": original,
            },
            version="v1",
        )
        response = await llm.ainvoke(rewrite_prompt)
        new_text = str(getattr(response, "content", response) or "").strip()
        if not new_text:
            return "LLM returned empty text; no changes applied."

        await apply_update(new_text)

        re_render_note = ""
        if target.startswith("slide_"):
            try:
                await carousel_agent.re_render_slides(project_uuid)
                re_render_note = " Slides + PDF re-rendered."
            except Exception as exc:
                re_render_note = f" Re-render skipped: {exc}"

        return (
            f"Updated {target} on project {project_id}. "
            f"New length: {len(new_text)} chars.{re_render_note}"
        )

    return refine_carousel_copy


def build_regenerate_slide_image_tool(
    carousel_agent: CarouselAgent,
) -> BaseTool:
    """Return the regenerate_slide_image tool closure."""

    @tool
    async def regenerate_slide_image(
        project_id: str,
        slide_number: int,
        instruction: str,
    ) -> str:
        """Regenerate the hero image for a specific carousel slide.

        Use when the user asks to change, update, or regenerate an image
        on a carousel slide they already generated.

        Args:
            project_id: UUID of the carousel project.
            slide_number: Which slide to regenerate (1-based index).
            instruction: Natural-language description of the desired change
                (e.g., "make it more futuristic", "change to a blue color
                scheme", "show a different scene").
        """
        from uuid import UUID as _UUID

        try:
            project_uuid = _UUID(project_id)
        except ValueError:
            return f"Invalid project_id {project_id!r} — expected a UUID."

        try:
            await carousel_agent.regenerate_slide_image(project_uuid, slide_number, instruction)
        except ValueError as exc:
            return f"Cannot regenerate image for slide {slide_number}: {exc}"
        except OSError as exc:
            return f"Image regeneration failed due to a file system error: {exc}"
        except RuntimeError as exc:
            return f"Image regeneration failed: {exc}"
        except Exception as exc:
            return f"Image regeneration failed unexpectedly: {exc}"

        return (
            f"Regenerated image for slide {slide_number} on project "
            f"{project_id}. Slides + PDF re-exported."
        )

    return regenerate_slide_image


def build_refine_carousel_design_tool(
    carousel_agent: CarouselAgent,
) -> BaseTool:
    """Return the refine_carousel_design tool closure."""

    @tool
    async def refine_carousel_design(
        project_id: str,
        instruction: str,
    ) -> str:
        """Apply a CSS/layout design change to an existing carousel.

        Use when the user asks to change sizing, spacing, fonts, image
        dimensions, padding, margins, or any visual layout property of
        the rendered carousel slides. This edits CSS only — it does NOT
        regenerate the source images.

        Args:
            project_id: UUID of the carousel project.
            instruction: Natural-language design request
                (e.g., "make the image on slide 3 bigger",
                "increase heading font size",
                "add more padding around the body text").
        """
        from uuid import UUID as _UUID

        try:
            project_uuid = _UUID(project_id)
        except ValueError:
            return f"Invalid project_id {project_id!r} — expected a UUID."

        try:
            await carousel_agent.refine_carousel_design(project_uuid, instruction)
        except ValueError as exc:
            return f"Cannot apply design change: {exc}"
        except OSError as exc:
            return f"Design refinement failed due to a file system error: {exc}"
        except RuntimeError as exc:
            return f"Design refinement failed: {exc}"
        except Exception as exc:
            return f"Design refinement failed unexpectedly: {exc}"

        return f"Applied design change to project {project_id}. Slides + PDF re-exported."

    return refine_carousel_design
