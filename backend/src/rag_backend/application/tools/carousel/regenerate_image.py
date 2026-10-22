"""Regenerate slide image tool for the RAG agent."""

from langchain_core.tools import BaseTool, tool

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.domain.constants.carousel_tools import (
    ERR_CAROUSEL_TOOL_UNEXPECTED,
)
from rag_backend.domain.protocols import CarouselRefinementService, CarouselRepository

from .access import CarouselToolAccessContext, load_authorized_project

_ERR_CANNOT_REGENERATE = "Cannot regenerate image for slide {slide_number}."


def build_regenerate_slide_image_tool(
    carousel_refinement: CarouselRefinementService,
    carousel_repository: CarouselRepository,
    access: CarouselToolAccessContext,
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
        loaded = await load_authorized_project(project_id, carousel_repository, access)
        if isinstance(loaded, str):
            return loaded
        project_uuid = loaded[0]

        safe_instruction = sanitize_llm_input(instruction)

        result = ERR_CAROUSEL_TOOL_UNEXPECTED
        try:
            await carousel_refinement.regenerate_slide_image(
                project_uuid, slide_number, safe_instruction
            )
            result = (
                f"Regenerated image for slide {slide_number} on project "
                f"{project_id}. Slides + PDF re-exported."
            )
        except ValueError:
            result = _ERR_CANNOT_REGENERATE.format(slide_number=slide_number)
        except Exception:
            result = ERR_CAROUSEL_TOOL_UNEXPECTED
        return result

    return regenerate_slide_image
