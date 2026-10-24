"""Which slides' structured items the editor shows as a single checklist line."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.carousel_access import reload_carousel_project
from rag_backend.api.schemas.carousel_workflow import EditorialWorkflowStateResponse
from rag_backend.application.services.carousel.localized_slide_builder import (
    resolve_slide_index,
    resolve_slide_type,
)
from rag_backend.application.services.carousel_template.role_layouts import (
    checklist_slide_numbers,
)
from rag_backend.domain.models import CarouselProject


def _slide_types(response: EditorialWorkflowStateResponse) -> dict[int, str]:
    """Slide number -> slide type, from the reviewed copy, else the drafts."""
    if response.localized_slides:
        return {
            slide.slide_index: slide.slide_type for slide in response.localized_slides
        }
    types: dict[int, str] = {}
    for position, draft in enumerate(response.slide_drafts, start=1):
        number = resolve_slide_index(draft, position)
        types[number] = resolve_slide_type(draft, number)
    return types


def apply_checklist_slides(
    response: EditorialWorkflowStateResponse,
    project: CarouselProject,
) -> EditorialWorkflowStateResponse:
    """Mark the slides that render their items as checklist lines (WYSIWYG editing)."""
    numbers = checklist_slide_numbers(project, _slide_types(response))
    return response.model_copy(update={"checklist_slide_indexes": sorted(numbers)})


async def with_checklist_slides(
    db: AsyncSession,
    project_id: UUID,
    response: EditorialWorkflowStateResponse,
) -> EditorialWorkflowStateResponse:
    """``apply_checklist_slides`` on the project as stored after the run.

    A response that does not compute the list would hand the client an empty one and
    wipe the checklist flags the editor holds.
    """
    project = await reload_carousel_project(db, project_id)
    return response if project is None else apply_checklist_slides(response, project)


__all__ = ["apply_checklist_slides", "with_checklist_slides"]
