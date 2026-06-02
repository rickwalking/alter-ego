"""Regenerate slide image tool for the RAG agent."""

from uuid import UUID

from langchain_core.tools import BaseTool, tool

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.domain.constants.access_control import ERR_CAROUSEL_TOOL_ACCESS_DENIED
from rag_backend.domain.constants.carousel_tools import (
    ERR_CAROUSEL_TOOL_INVALID_PROJECT_ID,
    ERR_CAROUSEL_TOOL_PROJECT_NOT_FOUND,
    ERR_CAROUSEL_TOOL_UNEXPECTED,
)
from rag_backend.domain.protocols import CarouselRefinementService, CarouselRepository

from .access import CarouselToolAccessContext, verify_carousel_tool_access

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
        try:
            project_uuid = UUID(project_id)
        except ValueError:
            return ERR_CAROUSEL_TOOL_INVALID_PROJECT_ID

        project = await carousel_repository.get_project_by_id(project_uuid)
        if project is None:
            return ERR_CAROUSEL_TOOL_PROJECT_NOT_FOUND
        access_error = verify_carousel_tool_access(project, access)
        if access_error is not None:
            return ERR_CAROUSEL_TOOL_ACCESS_DENIED

        safe_instruction = sanitize_llm_input(instruction)

        try:
            await carousel_refinement.regenerate_slide_image(
                project_uuid, slide_number, safe_instruction
            )
        except ValueError:
            return _ERR_CANNOT_REGENERATE.format(slide_number=slide_number)
        except (OSError, RuntimeError):
            return ERR_CAROUSEL_TOOL_UNEXPECTED
        except Exception:
            return ERR_CAROUSEL_TOOL_UNEXPECTED

        return (
            f"Regenerated image for slide {slide_number} on project "
            f"{project_id}. Slides + PDF re-exported."
        )

    return regenerate_slide_image
