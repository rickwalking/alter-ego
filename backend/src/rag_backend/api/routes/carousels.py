"""FastAPI routes for carousel content generation."""

import shutil
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from rag_backend.infrastructure.database.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.schemas import (
    CarouselBlogResponse,
    CarouselCaptionResponse,
    CarouselGenerateRequest,
    CarouselProjectCreate,
    CarouselProjectListResponse,
    CarouselProjectResponse,
    CarouselStatusResponse,
)
from rag_backend.domain.models import CarouselStatus
from rag_backend.domain.protocols import CarouselAgent, CarouselRepository

router = APIRouter(prefix="/carousels", tags=["carousels"])


def get_carousel_repo(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CarouselRepository:
    """Get carousel repository from DI container."""
    from rag_backend.infrastructure.container import get_container

    container = get_container()
    return container.carousel_repository(session=session)


def get_carousel_agent() -> CarouselAgent:
    """Get carousel agent from DI container."""
    from rag_backend.infrastructure.container import get_container

    container = get_container()
    return container.carousel_agent()


@router.post("", response_model=CarouselProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_carousel(
    request: CarouselProjectCreate,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselProjectResponse:
    """Create a new carousel project."""
    from rag_backend.domain.models import CarouselProject, CarouselTheme

    theme = CarouselTheme(request.theme)
    project = CarouselProject(
        topic=request.topic,
        audience=request.audience,
        niche=request.niche,
        slides_config=request.slides_config,
        language=request.language,
        generate_images=request.generate_images,
        theme=theme,
    )
    created = await repo.create_project(project)
    return CarouselProjectResponse.model_validate(created)


@router.get("", response_model=CarouselProjectListResponse)
async def list_carousels(
    status_filter: Annotated[CarouselStatus | None, Query(alias="status")] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)] = None,
) -> CarouselProjectListResponse:
    """List all carousel projects."""
    items = await repo.get_all_projects(status=status_filter, limit=limit, offset=offset)
    total = await repo.count(status=status_filter)
    return CarouselProjectListResponse(
        items=[CarouselProjectResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{project_id}", response_model=CarouselProjectResponse)
async def get_carousel(
    project_id: UUID,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselProjectResponse:
    """Get a carousel project by ID."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    return CarouselProjectResponse.model_validate(project)


@router.post("/{project_id}/generate", response_model=CarouselStatusResponse)
async def generate_carousel(
    project_id: UUID,
    request: CarouselGenerateRequest,
    agent: Annotated[CarouselAgent, Depends(get_carousel_agent)],
) -> CarouselStatusResponse:
    """Trigger the full carousel generation pipeline."""
    project = await agent.execute_pipeline(project_id)
    return CarouselStatusResponse.model_validate(project)


@router.get("/{project_id}/status", response_model=CarouselStatusResponse)
async def get_carousel_status(
    project_id: UUID,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselStatusResponse:
    """Check carousel generation status."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    return CarouselStatusResponse.model_validate(project)


@router.get("/{project_id}/blog", response_model=CarouselBlogResponse)
async def get_carousel_blog(
    project_id: UUID,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselBlogResponse:
    """Get the generated blog post for a carousel."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    if project.blog_markdown is None:
        raise HTTPException(status_code=404, detail="Blog post not yet generated")
    return CarouselBlogResponse(
        markdown=project.blog_markdown,
        title=project.title or project.topic,
        subtitle=project.subtitle,
    )


@router.post("/{project_id}/caption", response_model=CarouselCaptionResponse)
async def generate_caption(
    project_id: UUID,
    agent: Annotated[CarouselAgent, Depends(get_carousel_agent)],
) -> CarouselCaptionResponse:
    """Generate Instagram caption for a carousel."""
    project = await agent.execute_pipeline(project_id)
    return CarouselCaptionResponse(
        caption=project.caption or "",
        hashtags=[],
    )


@router.get("/{project_id}/download")
async def download_carousel(
    project_id: UUID,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> dict[str, str]:
    """Get download info for carousel files."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    if project.output_dir is None:
        raise HTTPException(status_code=404, detail="Carousel not yet generated")
    output_path = Path(project.output_dir)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output files not found")
    files = [str(p.relative_to(output_path)) for p in output_path.rglob("*") if p.is_file()]
    return {"output_dir": project.output_dir, "files": files}


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_carousel(
    project_id: UUID,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> None:
    """Delete a carousel project and its output files."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    if project.output_dir:
        output_path = Path(project.output_dir)
        if output_path.exists():
            shutil.rmtree(output_path)
    await repo.delete_project(project_id)
