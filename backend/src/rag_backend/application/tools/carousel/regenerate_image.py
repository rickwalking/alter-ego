"""Regenerate slide image tool for the RAG agent."""

from uuid import UUID

from langchain_core.tools import BaseTool, tool

from rag_backend.domain.protocols import CarouselAgent

_ERR_INVALID_PROJECT_ID = "Invalid project_id {!r} — expected a UUID."
_ERR_CANNOT_REGENERATE = "Cannot regenerate image for slide {slide_number}: {exc}"
_ERR_FILESYSTEM_ERROR = "Image regeneration failed due to a file system error: {exc}"
_ERR_RUNTIME_ERROR = "Image regeneration failed: {exc}"
_ERR_UNEXPECTED = "Image regeneration failed unexpectedly: {exc}"


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
        try:
            project_uuid = UUID(project_id)
        except ValueError:
            return _ERR_INVALID_PROJECT_ID.format(project_id)

        try:
            await carousel_agent.regenerate_slide_image(project_uuid, slide_number, instruction)
        except ValueError as exc:
            return _ERR_CANNOT_REGENERATE.format(slide_number=slide_number, exc=exc)
        except OSError as exc:
            return _ERR_FILESYSTEM_ERROR.format(exc=exc)
        except RuntimeError as exc:
            return _ERR_RUNTIME_ERROR.format(exc=exc)
        except Exception as exc:
            return _ERR_UNEXPECTED.format(exc=exc)

        return (
            f"Regenerated image for slide {slide_number} on project "
            f"{project_id}. Slides + PDF re-exported."
        )

    return regenerate_slide_image
