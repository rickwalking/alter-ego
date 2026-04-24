"""FastAPI routes for carousel content generation."""

import json
import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.params import Path as FastPath
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.carousel_orchestrator import CarouselAgent as CarouselAgentImpl
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
    InstagramPublishRequest,
    InstagramPublishResponse,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.domain.protocols import CarouselAgent, CarouselRepository, SocialPublisher
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.config import get_session

router = APIRouter(prefix="/carousels", tags=["carousels"])


_ERR_MISSING_PUBLIC_BASE_URL = (
    "CAROUSEL_PUBLIC_BASE_URL is not set — Instagram cannot "
    "fetch images from localhost. Configure a public HTTPS base "
    "URL in the backend .env."
)


def get_carousel_repo(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CarouselRepository:
    """Get a carousel repository bound to the per-request session."""
    return PostgresCarouselRepository(session)


def get_instagram_publisher() -> SocialPublisher:
    """Resolve the Instagram publisher from the DI container."""
    from rag_backend.infrastructure.container import get_container

    container = get_container()
    if bool(container.instagram_publisher.overridden):
        return container.instagram_publisher()
    return container.instagram_publisher()


def get_carousel_agent(
    request: Request,
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
    # Checkpointer is stashed on app.state by the lifespan context.
    checkpointer = getattr(request.app.state, "carousel_checkpointer", None)
    return CarouselAgentImpl(
        repository=PostgresCarouselRepository(session),
        llm_service=container.llm_service(),
        research_tool=container.research_tool(),
        image_registry=container.image_provider_registry(),
        export_service=container.export_service(),
        linkedin_post_generator=container.linkedin_post_generator(),
        pdf_slide_builder=container.pdf_slide_builder(),
        output_base_dir=settings.carousel_output_dir,
        checkpointer=checkpointer,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_carousel(
    request: CarouselProjectCreate,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
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
        image_model=request.image_model,
        image_style=request.image_style,
        theme=theme,
    )
    created = await repo.create_project(project)
    await session.commit()
    return CarouselProjectResponse.model_validate(created)


@router.get("")
async def list_carousels(
    status_filter: Annotated[CarouselStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
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


@router.get("/{project_id}")
async def get_carousel(
    project_id: UUID,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselProjectResponse:
    """Get a carousel project by ID."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    return CarouselProjectResponse.model_validate(project)


@router.post("/{project_id}/generate")
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


@router.get("/{project_id}/stream")
async def stream_carousel(
    project_id: UUID,
    agent: Annotated[CarouselAgent, Depends(get_carousel_agent)],
) -> StreamingResponse:
    """Stream pipeline progress as Server-Sent Events.

    Each event is `data: <json>\\n\\n` where the JSON object has
    `node`, `status`, and `phase_progress`. The frontend subscribes
    via EventSource (GET-only) and replaces its polling loop with push
    updates.
    """

    async def event_generator() -> AsyncIterator[str]:
        async for event in agent.stream_pipeline(project_id, seed_urls=None):
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{project_id}/resume")
async def resume_carousel(
    project_id: UUID,
    agent: Annotated[CarouselAgent, Depends(get_carousel_agent)],
) -> CarouselStatusResponse:
    """Resume an interrupted pipeline from its last checkpoint.

    Returns 503 when no checkpointer is configured (empty settings path,
    tests, or containerized envs without a writable volume). The
    idempotency hooks inside each node make expensive work (image API
    calls, slide rows) skip if already complete.
    """
    try:
        project = await agent.resume_pipeline(project_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Resume unavailable: {exc}",
        ) from exc
    return CarouselStatusResponse.model_validate(project)


@router.get("/{project_id}/status")
async def get_carousel_status(
    project_id: UUID,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselStatusResponse:
    """Check carousel generation status."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    return CarouselStatusResponse.model_validate(project)


def _pdf_path_for_language(project: CarouselProject, lang: str) -> str | None:
    """Pick the right PDF path for `lang`, falling back to PT when EN is missing."""
    if lang == "en":
        return project.pdf_path_en or project.pdf_path
    return project.pdf_path


@router.get("/{project_id}/pdf")
async def get_carousel_pdf(
    project_id: UUID,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    lang: Annotated[str, Query(pattern="^(pt|en)$")] = "pt",
) -> FileResponse:
    """Stream the carousel.pdf file for LinkedIn document posting.

    `lang=pt` (default) returns the Portuguese PDF; `lang=en` the
    English one. EN falls back to PT if not yet built.
    """
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    target_path = _pdf_path_for_language(project, lang)
    if not target_path:
        raise HTTPException(status_code=404, detail="PDF not yet generated")
    pdf_file = Path(target_path)
    if not pdf_file.exists():
        raise HTTPException(status_code=404, detail="PDF file missing on disk")
    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        filename=f"carousel-{project_id}-{lang}.pdf",
    )


@router.get("/{project_id}/blog")
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


@router.get("/{project_id}/blog/{lang}")
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

    title_subtitle_separator = ":"
    if title_subtitle_separator in heading:
        separator_pos = heading.index(title_subtitle_separator)
        title = heading[:separator_pos].strip()
        subtitle = heading[separator_pos + 1 :].strip()
        return title, subtitle

    return heading, None


@router.get("/{project_id}/design")
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
            rendered_slides_pt=tokens["images"].get("rendered_slides_pt"),
            rendered_slides_en=tokens["images"].get("rendered_slides_en"),
        ),
        layout=CarouselDesignLayout(**tokens["layout"]),
        theme_name=theme_name,
    )


_JPEG_CACHE_HEADERS = {"Cache-Control": "public, max-age=31536000"}


def _resolve_image_file(directory: Path, filename: str) -> Path | None:
    """Return `directory/filename`, trying a `.jpg` extension as fallback."""
    candidate = directory / filename
    if candidate.is_file():
        return candidate
    with_ext = Path(f"{candidate}.jpg")
    return with_ext if with_ext.is_file() else None


async def _load_project_with_output(project_id: UUID, repo: CarouselRepository) -> CarouselProject:
    """Fetch the project and 404 if missing or not yet exported."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    if project.output_dir is None:
        raise HTTPException(status_code=404, detail="Carousel not yet generated")
    return project


@router.get("/{project_id}/images/{filename}")
async def get_carousel_image(
    project_id: UUID,
    filename: str,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> FileResponse:
    """Serve a raw hero image (from <output>/images/)."""
    project = await _load_project_with_output(project_id, repo)
    image_path = _resolve_image_file(Path(project.output_dir or "") / "images", filename)
    if image_path is None:
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(
        path=str(image_path),
        media_type="image/jpeg",
        headers=_JPEG_CACHE_HEADERS,
    )


@router.get("/{project_id}/slide-images/{lang}/{filename}")
async def get_carousel_slide_image(
    project_id: UUID,
    lang: Annotated[str, FastPath(pattern="^(pt|en)$")],
    filename: str,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> FileResponse:
    """Serve a per-language rendered slide JPG (from <output>/<lang>/)."""
    project = await _load_project_with_output(project_id, repo)
    image_path = _resolve_image_file(Path(project.output_dir or "") / lang, filename)
    if image_path is None:
        raise HTTPException(status_code=404, detail=f"Slide image not found for {lang}")
    return FileResponse(
        path=str(image_path),
        media_type="image/jpeg",
        headers=_JPEG_CACHE_HEADERS,
    )


@router.get("/{project_id}/slides")
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


@router.post("/{project_id}/caption")
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


def _build_public_image_urls(project_id: UUID, slides_count: int = 4) -> list[str]:
    """Prepend CAROUSEL_PUBLIC_BASE_URL to each slide path.

    Meta fetches images server-side so localhost URLs won't work. If
    the base URL isn't configured we raise — the caller translates that
    into a 503 with an actionable hint.
    """
    from rag_backend.infrastructure.config.settings import get_settings

    base = get_settings().carousel_public_base_url.rstrip("/")
    if not base:
        raise RuntimeError(_ERR_MISSING_PUBLIC_BASE_URL)
    return [
        f"{base}/api/carousels/{project_id}/images/slide_{i}.jpg"
        for i in range(1, slides_count + 1)
    ]


@router.post(
    "/{project_id}/publish/instagram",
)
async def publish_to_instagram(
    project_id: UUID,
    body: InstagramPublishRequest,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    publisher: Annotated[SocialPublisher, Depends(get_instagram_publisher)],
) -> InstagramPublishResponse:
    """Publish the carousel's slides to Instagram with the provided caption."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    if project.status != CarouselStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Carousel is in status {project.status.value}; must be completed.",
        )

    try:
        image_urls = _build_public_image_urls(project_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    result = await publisher.publish_instagram(body.caption, image_urls)
    return InstagramPublishResponse(
        status=result.status,
        ig_post_id=result.post_id,
        error_message=result.error_message,
    )
