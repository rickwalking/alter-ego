"""Carousel-specific resource access helpers."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import ERR_CAROUSEL_NOT_FOUND
from rag_backend.domain.constants.access_control import (
    ERR_CAROUSEL_TOOL_ACCESS_DENIED,
    ERR_INVALID_REQUEST,
    ERR_SOURCE_NOT_FOUND,
)
from rag_backend.domain.constants.conversation import (
    CONVERSATION_METADATA_PROJECT_ID,
    ERR_ANONYMOUS_CAROUSEL_CONVERSATION,
    ERR_CAROUSEL_CONVERSATION_REQUIRES_AUTH,
    ERR_CONVERSATION_OWNERSHIP_DENIED,
)
from rag_backend.domain.models import Conversation, User
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.models import UserModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.source_comment import ContentSourceModel

from .resource_access import assert_domain_owner_or_admin, assert_owner_or_admin


@dataclass(frozen=True)
class ProjectSourceLookup:
    """Identifies a project source for access-controlled lookup."""

    project_id: UUID
    source_id: UUID
    user: UserModel


def _raise_workflow_access_denied() -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ERR_CAROUSEL_TOOL_ACCESS_DENIED,
    )


def _assert_workflow_project_access(
    project: CarouselProjectModel,
    user: UserModel,
) -> None:
    """Raise a uniform 403 when the user may not access workflow routes."""
    if _user_is_admin(user):
        return
    if _user_is_assigned_reviewer(project.assigned_reviewer_id, user):
        return
    if project.owner_id == user.id:
        return
    _raise_workflow_access_denied()


def _user_is_admin(user: UserModel) -> bool:
    return user.role == UserRole.ADMIN.value


def _user_is_assigned_reviewer(reviewer_id: str | None, user: UserModel) -> bool:
    return reviewer_id is not None and reviewer_id == user.id


async def validate_carousel_conversation_metadata(
    db: AsyncSession,
    metadata: dict[str, object],
    user: User | None,
) -> None:
    """Ensure carousel-bound conversations are authenticated and authorized."""
    if CONVERSATION_METADATA_PROJECT_ID not in metadata:
        return
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERR_CAROUSEL_CONVERSATION_REQUIRES_AUTH,
        )
    try:
        project_id = UUID(str(metadata[CONVERSATION_METADATA_PROJECT_ID]))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_INVALID_REQUEST,
        ) from exc
    user_model = await db.get(UserModel, str(user.id))
    if user_model is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERR_CAROUSEL_CONVERSATION_REQUIRES_AUTH,
        )
    await get_carousel_project_for_workflow_user(db, project_id, user_model)


def assert_carousel_conversation_chat_access(
    conversation: Conversation,
    user: User | None,
) -> None:
    """Require authenticated ownership for carousel-bound chat conversations."""
    if CONVERSATION_METADATA_PROJECT_ID not in conversation.metadata:
        return
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERR_CAROUSEL_CONVERSATION_REQUIRES_AUTH,
        )
    if conversation.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERR_ANONYMOUS_CAROUSEL_CONVERSATION,
        )
    if str(conversation.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERR_CONVERSATION_OWNERSHIP_DENIED,
        )


async def get_carousel_project_for_workflow_user(
    db: AsyncSession,
    project_id: UUID,
    user: UserModel,
) -> CarouselProjectModel:
    """Load a carousel project for editorial workflow routes."""
    project = await db.get(CarouselProjectModel, str(project_id))
    if project is None:
        _raise_workflow_access_denied()
    _assert_workflow_project_access(project, user)
    return project


async def get_carousel_project_for_user(
    db: AsyncSession,
    project_id: UUID,
    user: UserModel,
) -> CarouselProjectModel:
    """Load a carousel project and verify the caller may manage it."""
    project = await db.get(CarouselProjectModel, str(project_id))
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_CAROUSEL_NOT_FOUND,
        )
    assert_owner_or_admin(project.owner_id, user)
    return project


async def get_carousel_project_for_domain_user(
    db: AsyncSession,
    project_id: UUID,
    user: User,
) -> CarouselProjectModel:
    """Load a carousel project and verify ownership for domain User."""
    project = await db.get(CarouselProjectModel, str(project_id))
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_CAROUSEL_NOT_FOUND,
        )
    assert_domain_owner_or_admin(project.owner_id, user)
    return project


async def get_project_source_for_user(
    db: AsyncSession,
    lookup: ProjectSourceLookup,
) -> ContentSourceModel:
    """Load a project source after verifying carousel ownership."""
    await get_carousel_project_for_user(db, lookup.project_id, lookup.user)
    source = await db.get(ContentSourceModel, str(lookup.source_id))
    if source is None or source.project_id != str(lookup.project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_SOURCE_NOT_FOUND.format(source_id=lookup.source_id),
        )
    return source


__all__ = [
    "ERR_SOURCE_NOT_FOUND",
    "ProjectSourceLookup",
    "assert_carousel_conversation_chat_access",
    "get_carousel_project_for_domain_user",
    "get_carousel_project_for_user",
    "get_carousel_project_for_workflow_user",
    "get_project_source_for_user",
    "validate_carousel_conversation_metadata",
]
