"""Which slides' structured items the editor shows as a single checklist line."""

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


__all__ = ["apply_checklist_slides"]
