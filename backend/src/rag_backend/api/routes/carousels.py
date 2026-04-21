"""FastAPI routes for carousel content generation."""

import shutil
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.params import Path as FastPath
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.schemas import (
    CarouselBlogI18nResponse,
    CarouselBlogResponse,
    CarouselCaptionResponse,
    CarouselDesignColors,
    CarouselDesignImages,
    CarouselDesignLayout,
    CarouselDesignResponse,
    CarouselDesignTypography,
    CarouselGenerateRequest,
    CarouselProjectCreate,
    CarouselProjectListResponse,
    CarouselProjectResponse,
    CarouselSlideResponse,
    CarouselStatusResponse,
)
from rag_backend.application.services.carousel_agent import CarouselAgent as CarouselAgentImpl
from rag_backend.domain.models import CarouselStatus
from rag_backend.domain.protocols import CarouselAgent, CarouselRepository
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.config import get_session

router = APIRouter(prefix="/carousels", tags=["carousels"])


def get_carousel_repo(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CarouselRepository:
    """Get a carousel repository bound to the per-request session."""
    return PostgresCarouselRepository(session)


def get_carousel_agent(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CarouselAgent:
    """Build a CarouselAgent bound to the per-request session.

    container.carousel_agent() cannot be resolved synchronously in production
    because it depends on the async `db_session` Resource — calling it would
    return an `_asyncio.Future` rather than an instance. So we construct the
    agent directly from per-request repositories and session-free singletons.

    Tests that call `container.carousel_agent.override(...)` still work: an
    overridden provider returns its override directly (no dependency
    resolution), so we honor overrides here before the direct-construction
    path.
    """
    from rag_backend.infrastructure.container import get_container

    container = get_container()
    if bool(container.carousel_agent.overridden):
        return container.carousel_agent()

    settings = container.settings()
    return CarouselAgentImpl(
        repository=PostgresCarouselRepository(session),
        llm_service=container.llm_service(),
        research_tool=container.research_tool(),
        image_service=container.image_service(),
        export_service=container.export_service(),
        output_base_dir=settings.carousel_output_dir,
    )


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
    project = await agent.execute_pipeline(
        project_id,
        seed_urls=request.sources,
    )
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
    """Get the generated blog post for a carousel (default pt-BR)."""
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


@router.get("/{project_id}/blog/{lang}", response_model=CarouselBlogI18nResponse)
async def get_carousel_blog_i18n(
    project_id: UUID,
    lang: Annotated[str, FastPath(pattern="^(pt|en)$")],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselBlogI18nResponse:
    """Get the generated blog post in a specific language."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")

    blog_content = project.get_blog(lang)
    if blog_content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Blog post not available in '{lang}'",
            headers={"X-Available-Languages": ",".join(project.get_available_languages())},
        )

    translated_title, translated_subtitle = _extract_title_and_subtitle(blog_content)

    return CarouselBlogI18nResponse(
        markdown=blog_content,
        title=translated_title or project.title or project.topic,
        subtitle=translated_subtitle or project.subtitle,
        language=lang,
        available_languages=project.get_available_languages(),
    )


def _extract_title_and_subtitle(markdown: str) -> tuple[str | None, str | None]:
    """Extract title and subtitle from markdown first heading.

    The first line is expected to be '# Title: Subtitle' or '# Title'.
    """
    lines = markdown.strip().split("\n")
    if not lines:
        return None, None

    first_line = lines[0]
    if not first_line.startswith("# "):
        return None, None

    heading = first_line[2:].strip()

    TITLE_SUBTITLE_SEPARATOR = ":"
    if TITLE_SUBTITLE_SEPARATOR in heading:
        separator_pos = heading.index(TITLE_SUBTITLE_SEPARATOR)
        title = heading[:separator_pos].strip()
        subtitle = heading[separator_pos + 1 :].strip()
        return title, subtitle

    return heading, None


@router.get("/{project_id}/design", response_model=CarouselDesignResponse)
async def get_carousel_design(
    project_id: UUID,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselDesignResponse:
    """Get the visual design tokens for a carousel."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    if project.design_tokens is None:
        raise HTTPException(status_code=404, detail="Design tokens not yet generated")

    tokens = project.design_tokens
    theme_name = project.theme.value

    return CarouselDesignResponse(
        colors=CarouselDesignColors(**tokens["colors"]),
        typography=CarouselDesignTypography(**tokens["typography"]),
        images=CarouselDesignImages(
            hero=tokens["images"]["hero"],
            slides=tokens["images"]["slides"],
        ),
        layout=CarouselDesignLayout(**tokens["layout"]),
        theme_name=theme_name,
    )


@router.get("/{project_id}/images/{filename}")
async def get_carousel_image(
    project_id: UUID,
    filename: str,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> FileResponse:
    """Serve a carousel image file."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    if project.output_dir is None:
        raise HTTPException(status_code=404, detail="Carousel not yet generated")
    images_dir = Path(project.output_dir) / "images"
    image_path = images_dir / filename
    if not image_path.is_file():
        image_path = Path(str(image_path) + ".jpg")
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(
        path=str(image_path),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000"},
    )


@router.get("/{project_id}/slides", response_model=list[CarouselSlideResponse])
async def get_carousel_slides(
    project_id: UUID,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> list[CarouselSlideResponse]:
    """Get all slides for a carousel project."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    slides = await repo.get_slides_by_project(project_id)
    return [CarouselSlideResponse.model_validate(s) for s in slides]


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
