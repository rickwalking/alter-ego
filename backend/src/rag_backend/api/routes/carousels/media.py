"""Carousel media + serving routes (pdf / blog / design / images / slides).

Thin HTTP adapters (AE-0120). Each endpoint reads the project/slides through the
presentation :class:`PresentationHandlers` (via the presentation facade), applies
the access check at the edge (``assert_domain_owner_or_admin`` /
``assert_carousel_public``), and builds the FileResponse / response schema. The
design-token merge is reached through the handler (the AE-0115 §6 presentation
read) instead of importing the merge utility directly; the routes no longer
construct the carousel repository.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.params import Path as FastPath
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import (
    ERR_BLOG_NOT_GENERATED,
    ERR_CAROUSEL_NOT_FOUND,
    ERR_CAROUSEL_NOT_GENERATED,
    ERR_DESIGN_NOT_GENERATED,
    ERR_FORBIDDEN,
    ERR_IMAGE_NOT_FOUND,
    ERR_NOT_AUTHENTICATED,
    ERR_NOT_FOUND,
    ERR_OUTPUT_NOT_FOUND,
    ERR_PDF_NOT_GENERATED,
    MEDIA_TYPE_JPEG,
    MEDIA_TYPE_PDF,
)
from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.presentation import get_presentation_handlers
from rag_backend.api.dependencies.publishing import (
    PublishingComposition,
    build_publishing_module,
)
from rag_backend.api.dependencies.resource_access import assert_domain_owner_or_admin
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas import (
    CarouselBlogI18nResponse,
    CarouselBlogResponse,
    CarouselDesignColors,
    CarouselDesignImages,
    CarouselDesignLayout,
    CarouselDesignResponse,
    CarouselDesignTypography,
    CarouselSlideResponse,
)
from rag_backend.application.services.carousel.artifact_path_resolver import (
    resolve_shared_images_dir,
    resolve_slide_image_path,
)
from rag_backend.domain.constants import SWIPE_TEXT_EN
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_CAROUSEL_PUBLISH
from rag_backend.domain.models import CarouselProject, User
from rag_backend.modules.presentation import PresentationHandlers
from rag_backend.modules.publishing import (
    CarouselRepository,
    PublishingModule,
)

from .deps import get_carousel_repo
from .helpers import (
    _JPEG_CACHE_HEADERS,
    _resolve_image_file,
    _resolve_pdf_file,
    _safe_relative_file_path,
    assert_carousel_public,
)

router = APIRouter()

PresentationHandlersDep = Annotated[
    PresentationHandlers, Depends(get_presentation_handlers)
]


def get_publishing_module_for_blog_read(
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PublishingModule:
    """Build the request-scoped publishing facade for the carousel-blog read edge.

    Binds the read projection port to the request session (the sole carousel/blog
    ORM read seam → the AE-0127 ``origin='carousel'`` backfill lookup with the
    embedded-column fallback). The carousel repository is resolved via the
    grandfathered ``get_carousel_repo`` edge so this route adds no new
    ``api -> infrastructure`` import.
    """
    return build_publishing_module(
        PublishingComposition(
            session=session, carousel_repository=repo, with_read=True
        ),
    )


async def _load_project_or_404(
    handlers: PresentationHandlers,
    project_id: UUID,
) -> CarouselProject:
    project = await handlers.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    return project


async def _load_project_with_output(
    handlers: PresentationHandlers,
    project_id: UUID,
) -> CarouselProject:
    project = await _load_project_or_404(handlers, project_id)
    if project.output_dir is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_GENERATED)
    return project


@router.get(
    "/{project_id}/pdf",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def get_carousel_pdf(
    request: Request,
    project_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    handlers: PresentationHandlersDep,
    lang: Annotated[str, Query(pattern="^(pt|en)$")] = "pt",
) -> FileResponse:
    """Stream the carousel.pdf file for LinkedIn document posting."""
    project = await _load_project_or_404(handlers, project_id)
    assert_domain_owner_or_admin(project.owner_id, user)
    pdf_file = _resolve_pdf_file(project, lang)
    if pdf_file is None:
        raise HTTPException(status_code=404, detail=ERR_PDF_NOT_GENERATED)
    return FileResponse(
        path=str(pdf_file),
        media_type=MEDIA_TYPE_PDF,
        filename=f"carousel-{project_id}-{lang}.pdf",
    )


@router.get(
    "/{project_id}/blog",
    responses={
        404: {"description": ERR_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def get_carousel_blog(
    request: Request,
    project_id: UUID,
    handlers: PresentationHandlersDep,
    publishing: Annotated[
        PublishingModule, Depends(get_publishing_module_for_blog_read)
    ],
) -> CarouselBlogResponse:
    """Get the generated blog post for a carousel (default pt-BR)."""
    project = await _load_project_or_404(handlers, project_id)
    assert_carousel_public(project)
    projection = await publishing.service.project_carousel_blog(project)
    if projection is None:
        raise HTTPException(status_code=404, detail=ERR_BLOG_NOT_GENERATED)
    return CarouselBlogResponse(
        markdown=projection.markdown,
        title=projection.title,
        subtitle=projection.subtitle,
    )


@router.get(
    "/{project_id}/blog/{lang}",
    responses={
        404: {"description": ERR_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def get_carousel_blog_i18n(
    request: Request,
    project_id: UUID,
    lang: Annotated[str, FastPath(pattern="^(pt|en)$")],
    handlers: PresentationHandlersDep,
    publishing: Annotated[
        PublishingModule, Depends(get_publishing_module_for_blog_read)
    ],
) -> CarouselBlogI18nResponse:
    """Get the generated blog post in a specific language."""

    project = await _load_project_or_404(handlers, project_id)
    assert_carousel_public(project)

    projection = await publishing.service.project_carousel_blog_i18n(project, lang)
    if projection is None:
        raise HTTPException(
            status_code=404,
            detail=f"Blog post not available in '{lang}'",
            headers={
                "X-Available-Languages": ",".join(project.get_available_languages())
            },
        )

    return CarouselBlogI18nResponse(
        markdown=projection.markdown,
        title=projection.title,
        subtitle=projection.subtitle,
        language=projection.language,
        available_languages=projection.available_languages,
    )


@router.get(
    "/{project_id}/design",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        404: {"description": ERR_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def get_carousel_design(
    request: Request,
    project_id: UUID,
    handlers: PresentationHandlersDep,
    lang: Annotated[str, Query(pattern="^(pt|en)$")] = "pt",
) -> CarouselDesignResponse:
    """Get the visual design tokens for a carousel."""
    project = await _load_project_or_404(handlers, project_id)
    assert_carousel_public(project)
    if project.design_tokens is None:
        raise HTTPException(status_code=404, detail=ERR_DESIGN_NOT_GENERATED)

    raw_tokens = project.design_tokens
    theme_name = project.theme.value

    required_keys = ("colors", "typography", "images", "layout")
    defaults = handlers.merge_design_tokens(project)
    if not raw_tokens or not all(k in raw_tokens for k in required_keys):
        tokens: dict[str, object] = defaults
    else:
        tokens = defaults

    layout = dict(tokens["layout"])
    layout["swipe_text"] = SWIPE_TEXT_EN

    return CarouselDesignResponse(
        colors=CarouselDesignColors(**tokens["colors"]),
        typography=CarouselDesignTypography(**tokens["typography"]),
        images=CarouselDesignImages(
            hero=tokens["images"]["hero"],
            slides=tokens["images"]["slides"],
            rendered_slides_pt=tokens["images"].get("rendered_slides_pt"),
            rendered_slides_en=tokens["images"].get("rendered_slides_en"),
            blog_image_map=tokens["images"].get("blog_image_map"),
        ),
        layout=CarouselDesignLayout(**layout),
        theme_name=theme_name,
    )


@router.get(
    "/{project_id}/images/{filename}",
    responses={
        404: {"description": ERR_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def get_carousel_image(
    request: Request,
    project_id: UUID,
    filename: str,
    handlers: PresentationHandlersDep,
) -> FileResponse:
    """Serve a raw hero image (from <output>/images/)."""
    project = await _load_project_with_output(handlers, project_id)
    assert_carousel_public(project)
    images_dir = resolve_shared_images_dir(project)
    if images_dir is None:
        raise HTTPException(status_code=404, detail=ERR_IMAGE_NOT_FOUND)
    image_path = _resolve_image_file(images_dir, filename)
    if image_path is None:
        raise HTTPException(status_code=404, detail=ERR_IMAGE_NOT_FOUND)
    return FileResponse(
        path=str(image_path),
        media_type=MEDIA_TYPE_JPEG,
        headers=_JPEG_CACHE_HEADERS,
    )


@router.get(
    "/{project_id}/slide-images/{lang}/{filename}",
    responses={
        404: {"description": ERR_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def get_carousel_slide_image(
    request: Request,
    project_id: UUID,
    lang: Annotated[str, FastPath(pattern="^(pt|en)$")],
    filename: str,
    handlers: PresentationHandlersDep,
) -> FileResponse:
    """Serve a per-language rendered slide JPG (from <output>/<lang>/)."""
    project = await _load_project_with_output(handlers, project_id)
    assert_carousel_public(project)
    image_path = resolve_slide_image_path(project, lang, filename)
    if image_path is None:
        image_path = _resolve_image_file(
            Path(project.output_dir or "") / lang,
            filename,
        )
    if image_path is None:
        raise HTTPException(status_code=404, detail=f"Slide image not found for {lang}")
    return FileResponse(
        path=str(image_path),
        media_type=MEDIA_TYPE_JPEG,
        headers=_JPEG_CACHE_HEADERS,
    )


@router.get(
    "/{project_id}/slides",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        404: {"description": ERR_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def get_carousel_slides(
    request: Request,
    project_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    handlers: PresentationHandlersDep,
) -> list[CarouselSlideResponse]:
    """Get all slides for a carousel project."""
    project = await _load_project_or_404(handlers, project_id)
    assert_domain_owner_or_admin(project.owner_id, user)
    slides = await handlers.get_slides(project_id)
    return [CarouselSlideResponse.model_validate(s) for s in slides]


@router.get(
    "/{project_id}/download",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def download_carousel(
    request: Request,
    project_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    handlers: PresentationHandlersDep,
) -> dict[str, list[str]]:
    """Get download info for carousel files."""
    project = await _load_project_or_404(handlers, project_id)
    assert_domain_owner_or_admin(project.owner_id, user)
    if project.output_dir is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_GENERATED)
    output_path = Path(project.output_dir).resolve()
    if not output_path.is_dir():
        raise HTTPException(status_code=404, detail=ERR_OUTPUT_NOT_FOUND)
    files = [
        relative
        for path in output_path.rglob("*")
        if (relative := _safe_relative_file_path(path, output_path)) is not None
    ]
    return {"files": files}
