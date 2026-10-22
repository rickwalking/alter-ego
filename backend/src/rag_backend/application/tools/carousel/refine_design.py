"""Refine carousel design tool for the RAG agent."""

from langchain_core.tools import BaseTool, tool

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.domain.constants.carousel_tools import (
    ERR_CAROUSEL_TOOL_UNEXPECTED,
)
from rag_backend.domain.protocols import CarouselRefinementService, CarouselRepository

from .access import CarouselToolAccessContext, load_authorized_project

_ERR_CANNOT_APPLY = "Cannot apply design change to this carousel."


def build_refine_carousel_design_tool(
    carousel_refinement: CarouselRefinementService,
    carousel_repository: CarouselRepository,
    access: CarouselToolAccessContext,
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
        loaded = await load_authorized_project(project_id, carousel_repository, access)
        if isinstance(loaded, str):
            return loaded
        project_uuid = loaded[0]

        safe_instruction = sanitize_llm_input(instruction)

        try:
            await carousel_refinement.refine_carousel_design(
                project_uuid, safe_instruction
            )
        except ValueError:
            return _ERR_CANNOT_APPLY
        except (OSError, RuntimeError):
            return ERR_CAROUSEL_TOOL_UNEXPECTED
        except Exception:
            return ERR_CAROUSEL_TOOL_UNEXPECTED

        return (
            f"Applied design change to project {project_id}. Slides + PDF re-exported."
        )

    return refine_carousel_design
