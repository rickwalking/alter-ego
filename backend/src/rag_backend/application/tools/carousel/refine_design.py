"""Refine carousel design tool for the RAG agent."""

from uuid import UUID

from langchain_core.tools import BaseTool, tool

from rag_backend.domain.protocols import CarouselAgent

_ERR_INVALID_PROJECT_ID = "Invalid project_id {!r} — expected a UUID."
_ERR_CANNOT_APPLY = "Cannot apply design change: {exc}"
_ERR_FILESYSTEM_ERROR = "Design refinement failed due to a file system error: {exc}"
_ERR_RUNTIME_ERROR = "Design refinement failed: {exc}"
_ERR_UNEXPECTED = "Design refinement failed unexpectedly: {exc}"


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
        try:
            project_uuid = UUID(project_id)
        except ValueError:
            return _ERR_INVALID_PROJECT_ID.format(project_id)

        try:
            await carousel_agent.refine_carousel_design(project_uuid, instruction)
        except ValueError as exc:
            return _ERR_CANNOT_APPLY.format(exc=exc)
        except OSError as exc:
            return _ERR_FILESYSTEM_ERROR.format(exc=exc)
        except RuntimeError as exc:
            return _ERR_RUNTIME_ERROR.format(exc=exc)
        except Exception as exc:
            return _ERR_UNEXPECTED.format(exc=exc)

        return (
            f"Applied design change to project {project_id}. Slides + PDF re-exported."
        )

    return refine_carousel_design
