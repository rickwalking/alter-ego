import shutil
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import (
    ERR_CAROUSEL_NOT_FOUND,
    ERR_FORBIDDEN,
    ERR_NOT_AUTHENTICATED,
    ERR_NOT_FOUND,
)
from rag_backend.api.dependencies import (
    get_optional_user,
    require_authenticated_user,
    require_editor_or_admin,
)
from rag_backend.api.schemas import (
    CarouselProjectCreate,
    CarouselProjectListResponse,
    CarouselProjectResponse,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus, User
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.infrastructure.database.config import get_session

from .deps import get_carousel_repo

router = APIRouter()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
         401: {"description": ERR_NOT_AUTHENTICATED},
         403: {"description": ERR_FORBIDDEN},
    },
)
async def create_carousel(
    request: CarouselProjectCreate,
    user: Annotated[User, Depends(require_editor_or_admin)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CarouselProjectResponse:
    """Create a new carousel project."""
    from rag_backend.domain.models import CarouselTheme

    theme = CarouselTheme(request.theme)
    project = CarouselProject(
        topic=request.topic,
        audience=request.audience,
        niche=request.niche,
        slides_config=request.slides_config,
        language=request.language,
        generate_images=request.generate_images,
        image_model=request.image_model,
        image_style=request.image_style,
        theme=theme,
    )
    created = await repo.create_project(project)
    await session.commit()
    return CarouselProjectResponse.model_validate(created)


@router.get(
    "",
    responses={
         401: {"description": ERR_NOT_AUTHENTICATED},
    },
)
async def list_carousels(
    user: Annotated[User | None, Depends(get_optional_user)],
    status_filter: Annotated[CarouselStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)] = None,
) -> CarouselProjectListResponse:
    """List all carousel projects. Publicly accessible for completed projects."""
    items = await repo.get_all_projects(status=status_filter, limit=limit, offset=offset)
    total = await repo.count(status=status_filter)
    return CarouselProjectListResponse(
        items=[CarouselProjectResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{project_id}",
    responses={
         401: {"description": ERR_NOT_AUTHENTICATED},
         403: {"description": ERR_FORBIDDEN},
         404: {"description": ERR_NOT_FOUND},
    },
)
async def get_carousel(
    project_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselProjectResponse:
    """Get a carousel project by ID."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    return CarouselProjectResponse.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
         401: {"description": ERR_NOT_AUTHENTICATED},
         403: {"description": ERR_FORBIDDEN},
         404: {"description": ERR_NOT_FOUND},
    },
)
async def delete_carousel(
    project_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> None:
    """Delete a carousel project and its output files."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    if project.output_dir:
        output_path = Path(project.output_dir)
        if output_path.exists():
            shutil.rmtree(output_path)
    await repo.delete_project(project_id)
