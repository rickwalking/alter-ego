"""Access checks for RAG carousel agent tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from rag_backend.domain.constants.access_control import ERR_CAROUSEL_TOOL_ACCESS_DENIED
from rag_backend.domain.constants.carousel_tools import (
    ERR_CAROUSEL_TOOL_INVALID_PROJECT_ID,
    ERR_CAROUSEL_TOOL_PROJECT_NOT_FOUND,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import CarouselRepository

DefaultRubricLookup = Callable[[], Awaitable[str | None]]


@dataclass(frozen=True)
class CarouselToolAccessContext:
    """Caller identity scoped to a carousel chat conversation.

    ``default_rubric_id`` resolves the default carousel rubric a chat-created
    carousel gets (none when unset).
    """

    owner_user_id: str
    bound_project_id: str | None = None
    default_rubric_id: DefaultRubricLookup | None = None


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


async def load_authorized_project(
    project_id: str,
    repository: CarouselRepository,
    access: CarouselToolAccessContext,
) -> tuple[UUID, CarouselProject] | str:
    """Return the parsed id and project, or the tool error string to hand back."""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return ERR_CAROUSEL_TOOL_INVALID_PROJECT_ID
    project = await repository.get_project_by_id(project_uuid)
    if project is None:
        return ERR_CAROUSEL_TOOL_PROJECT_NOT_FOUND
    if verify_carousel_tool_access(project, access) is not None:
        return ERR_CAROUSEL_TOOL_ACCESS_DENIED
    return project_uuid, project


__all__ = [
    "CarouselToolAccessContext",
    "load_authorized_project",
    "verify_carousel_tool_access",
    "verify_carousel_workflow_start_access",
]
