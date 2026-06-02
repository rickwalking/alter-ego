"""Access checks for RAG carousel agent tools."""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.domain.constants.access_control import ERR_CAROUSEL_TOOL_ACCESS_DENIED
from rag_backend.domain.models import CarouselProject


@dataclass(frozen=True)
class CarouselToolAccessContext:
    """Caller identity scoped to a carousel chat conversation."""

    owner_user_id: str
    bound_project_id: str | None = None


def verify_carousel_tool_access(
    project: CarouselProject,
    access: CarouselToolAccessContext,
) -> str | None:
    """Return an error message when the caller may not mutate the project."""
    if access.bound_project_id and str(project.id) != access.bound_project_id:
        return ERR_CAROUSEL_TOOL_ACCESS_DENIED
    return verify_carousel_workflow_start_access(project, access)


def verify_carousel_workflow_start_access(
    project: CarouselProject,
    access: CarouselToolAccessContext,
) -> str | None:
    """Return an error when the caller may not start workflow on the project."""
    if project.owner_id is None:
        return ERR_CAROUSEL_TOOL_ACCESS_DENIED
    if project.owner_id != access.owner_user_id:
        return ERR_CAROUSEL_TOOL_ACCESS_DENIED
    return None


__all__ = [
    "CarouselToolAccessContext",
    "verify_carousel_tool_access",
    "verify_carousel_workflow_start_access",
]
