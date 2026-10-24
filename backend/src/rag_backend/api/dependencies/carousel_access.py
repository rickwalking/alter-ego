"""Carousel-specific resource access helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import ERR_CAROUSEL_NOT_FOUND
from rag_backend.api.schemas.knowledge_sources import (
    CarouselSourceFacet,
    CarouselSourceItem,
    CarouselSourceListResponse,
)
from rag_backend.domain.constants.access_control import (
    ERR_CAROUSEL_TOOL_ACCESS_DENIED,
    ERR_INVALID_REQUEST,
    ERR_SOURCE_NOT_FOUND,
)
from rag_backend.domain.constants.carousel_archive import ARCHIVE_REFUSED_IN_PROGRESS
from rag_backend.domain.constants.conversation import (
    CONVERSATION_METADATA_PROJECT_ID,
    ERR_ANONYMOUS_CAROUSEL_CONVERSATION,
    ERR_CAROUSEL_CONVERSATION_REQUIRES_AUTH,
    ERR_CONVERSATION_OWNERSHIP_DENIED,
)
from rag_backend.domain.models import CarouselProject, Conversation, User
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.models import (
    UserModel,
    archivable,
    archive_refusal_of,
    archive_where,
    heartbeat_stale_seconds,
)
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


async def reload_carousel_project(
    db: AsyncSession, project_id: UUID
) -> CarouselProject | None:
    """The project as stored now, ``None`` when missing (no access check).

    Every column is re-read (``populate_existing``), so a row the session already
    holds with expired attributes is never lazy-loaded.
    """
    row = await db.get(CarouselProjectModel, str(project_id), populate_existing=True)
    return row.to_entity() if row is not None else None


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
    "reload_carousel_project",
    "validate_carousel_conversation_metadata",
]


_Row = TypeVar("_Row", bound=tuple[object, ...])

SOURCE_TYPE_URL = "url"
"""The content-source type whose body is the source's URL."""

_URL_PREFIXES = ("http://", "https://")


@dataclass(frozen=True)
class CarouselSourceQuery:
    """A page of the caller's carousel sources, optionally of one carousel."""

    user: UserModel
    limit: int
    offset: int
    project_id: UUID | None = None


def _for_owner(statement: Select[_Row], user: UserModel) -> Select[_Row]:
    """Join the statement's sources to their carousel and keep the caller's own."""
    joined = statement.join(
        CarouselProjectModel,
        CarouselProjectModel.id == ContentSourceModel.project_id,
    )
    if _user_is_admin(user):
        return joined
    return joined.where(CarouselProjectModel.owner_id == user.id)


def _source_url(source: ContentSourceModel) -> str | None:
    """The URL of a URL source (its body), or ``None`` for any other source."""
    content = str(source.content or "").strip()
    if source.source_type != SOURCE_TYPE_URL or not content.startswith(_URL_PREFIXES):
        return None
    return content


def _to_item(
    source: ContentSourceModel, project_title: str | None
) -> CarouselSourceItem:
    """The listing row of one source."""
    return CarouselSourceItem(
        id=UUID(str(source.id)),
        title=str(source.title),
        source_type=str(source.source_type),
        url=_source_url(source),
        project_id=UUID(str(source.project_id)),
        project_title=project_title or "",
        created_at=source.created_at,
    )


async def _carousel_facets(
    db: AsyncSession, query: CarouselSourceQuery
) -> list[CarouselSourceFacet]:
    """Every carousel of the caller that has sources, with its source count."""
    statement = (
        _for_owner(
            select(
                CarouselProjectModel.id,
                CarouselProjectModel.title,
                func.count(ContentSourceModel.id),
            ),
            query.user,
        )
        .group_by(CarouselProjectModel.id, CarouselProjectModel.title)
        .order_by(CarouselProjectModel.title)
    )
    rows = (await db.execute(statement)).all()
    return [
        CarouselSourceFacet(
            project_id=UUID(str(project_id)), title=title or "", count=int(count)
        )
        for project_id, title, count in rows
    ]


async def list_carousel_sources_for_user(
    db: AsyncSession, query: CarouselSourceQuery
) -> CarouselSourceListResponse:
    """A page of the caller's carousel sources, newest first; an admin sees all."""
    statement = _for_owner(
        select(ContentSourceModel, CarouselProjectModel.title), query.user
    )
    if query.project_id is not None:
        statement = statement.where(
            ContentSourceModel.project_id == str(query.project_id)
        )
    total = await db.scalar(select(func.count()).select_from(statement.subquery()))
    page = await db.execute(
        statement
        .order_by(ContentSourceModel.created_at.desc(), ContentSourceModel.id)
        .limit(query.limit)
        .offset(query.offset)
    )
    return CarouselSourceListResponse(
        items=[_to_item(source, title) for source, title in page.all()],
        total=int(total or 0),
        limit=query.limit,
        offset=query.offset,
        carousels=await _carousel_facets(db, query),
    )


async def archive_carousel_project(
    db: AsyncSession, project: CarouselProjectModel, now: datetime
) -> CarouselArchiveOutcome:
    """Archive ``project`` under the archive rules in one conditional UPDATE.

    The rules are checked by the write itself, so a run or an autopilot publish
    that started after the caller's access check is never archived. Nothing is
    committed when the archive is refused.
    """
    stale_seconds = heartbeat_stale_seconds()
    predicates = [
        CarouselProjectModel.id == str(project.id),
        *archivable(now, stale_seconds),
    ]
    if await archive_where(db, predicates, now):
        await db.commit()
        return CarouselArchiveOutcome(archived_at=now)
    await db.refresh(project)
    if project.archived_at is not None:
        return CarouselArchiveOutcome(archived_at=project.archived_at)
    refusal = await archive_refusal_of(db, str(project.id), (now, stale_seconds))
    return CarouselArchiveOutcome(refusal=refusal or ARCHIVE_REFUSED_IN_PROGRESS)


@dataclass(frozen=True)
class CarouselArchiveOutcome:
    """The archive time of an archived carousel, or why it was refused."""

    archived_at: datetime | None = None
    refusal: str | None = None
