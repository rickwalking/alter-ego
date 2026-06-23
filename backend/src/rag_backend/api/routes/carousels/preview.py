"""Authenticated preview routes for draft carousel content.

Thin HTTP adapters (AE-0120). Each endpoint reads the project + the assigned
reviewer id through the presentation :class:`PresentationHandlers` (via the
presentation facade), applies the preview access check at the edge
(``assert_carousel_project_access``), and builds the response / FileResponse. The
design-token merge is reached through the handler (the AE-0115 §6 presentation
read); the routes no longer construct the carousel repository or import the
carousel ORM.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.params import Path as FastPath
from fastapi.responses import FileResponse

from rag_backend.api.constants import (
    CAROUSEL_PREVIEW_CACHE_HEADERS,
    ERR_CAROUSEL_NOT_FOUND,
    ERR_CAROUSEL_NOT_GENERATED,
    ERR_DESIGN_NOT_GENERATED,
    ERR_FORBIDDEN,
    ERR_IMAGE_NOT_FOUND,
    ERR_NOT_AUTHENTICATED,
    ERR_NOT_FOUND,
    MEDIA_TYPE_JPEG,
)
from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.dependencies.presentation import get_presentation_handlers
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas import (
    CarouselBlogI18nResponse,
    CarouselDesignColors,
    CarouselDesignImages,
    CarouselDesignLayout,
    CarouselDesignResponse,
    CarouselDesignTypography,
)
from rag_backend.domain.constants import (
    HD_SUBDIR_NAME,
    SHARED_IMAGES_DIR_NAME,
)
from rag_backend.domain.constants.blog_language import (
    BLOG_LANGUAGE_EN,
    BLOG_LANGUAGE_PT,
    CAROUSEL_SWIPE_TEXT_EN,
    CAROUSEL_SWIPE_TEXT_PT,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_CAROUSEL_PUBLISH
from rag_backend.domain.models import CarouselProject, User
from rag_backend.modules.presentation import PresentationHandlers

from .helpers import (
    _PREVIEW_JPEG_CACHE_HEADERS,
    _extract_first_paragraph,
    _extract_title_and_subtitle,
    _resolve_image_file,
    assert_carousel_project_access,
)

router = APIRouter()

PresentationHandlersDep = Annotated[
    PresentationHandlers, Depends(get_presentation_handlers)
]


@dataclass(frozen=True)
class PreviewAccessContext:
    """Shared dependencies for authenticated carousel preview routes."""

    project_id: UUID
    user: User
    handlers: PresentationHandlers


async def _load_accessible_project(ctx: PreviewAccessContext) -> CarouselProject:
    project = await ctx.handlers.get_project(ctx.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    assigned_reviewer_id = await ctx.handlers.get_assigned_reviewer_id(ctx.project_id)
    assert_carousel_project_access(
        project,
        ctx.user,
        assigned_reviewer_id=assigned_reviewer_id,
    )
    return project


async def _load_accessible_project_with_output(
    ctx: PreviewAccessContext,
) -> CarouselProject:
    project = await ctx.handlers.get_project(ctx.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    if project.output_dir is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_GENERATED)
    assigned_reviewer_id = await ctx.handlers.get_assigned_reviewer_id(ctx.project_id)
    assert_carousel_project_access(
        project,
        ctx.user,
        assigned_reviewer_id=assigned_reviewer_id,
    )
    return project


def _resolve_blog_preview_titles(
    lang: str,
    blog_content: str,
    project: CarouselProject,
) -> tuple[str, str | None]:
    translated_title, translated_subtitle = _extract_title_and_subtitle(blog_content)
    if lang == BLOG_LANGUAGE_EN:
        title = translated_title or project.title_en or project.title or project.topic
        subtitle = (
            translated_subtitle
            or project.subtitle_en
            or _extract_first_paragraph(blog_content)
            or project.subtitle
        )
        return title, subtitle
    title = translated_title or project.title or project.topic
    subtitle = translated_subtitle or project.subtitle
    return title, subtitle


def _swipe_text_for_language(lang: str) -> str:
    if lang == BLOG_LANGUAGE_EN:
        return CAROUSEL_SWIPE_TEXT_EN
    return CAROUSEL_SWIPE_TEXT_PT


@router.get(
    "/{project_id}/preview/blog/{lang}",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def preview_carousel_blog(
    request: Request,
    project_id: UUID,
    lang: Annotated[str, FastPath(pattern="^(pt|en)$")],
    user: Annotated[User, Depends(require_authenticated_user)],
    handlers: PresentationHandlersDep,
    response: Response,
) -> CarouselBlogI18nResponse:
    """Preview draft blog content for authenticated project owners."""
    ctx = PreviewAccessContext(project_id=project_id, user=user, handlers=handlers)
    project = await _load_accessible_project(ctx)
    response.headers.update(CAROUSEL_PREVIEW_CACHE_HEADERS)

    blog_content = project.get_blog(lang)
    if blog_content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Blog post not available in '{lang}'",
            headers={
                "X-Available-Languages": ",".join(project.get_available_languages())
            },
        )

    title, subtitle = _resolve_blog_preview_titles(lang, blog_content, project)

    return CarouselBlogI18nResponse(
        markdown=blog_content,
        title=title,
        subtitle=subtitle,
        language=lang,
        available_languages=project.get_available_languages(),
    )


@router.get(
    "/{project_id}/preview/design/{lang}",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def preview_carousel_design(
    request: Request,
    project_id: UUID,
    lang: Annotated[str, FastPath(pattern="^(pt|en)$")],
    user: Annotated[User, Depends(require_authenticated_user)],
    handlers: PresentationHandlersDep,
    response: Response,
) -> CarouselDesignResponse:
    """Preview draft design tokens for authenticated project owners."""
    ctx = PreviewAccessContext(project_id=project_id, user=user, handlers=handlers)
    project = await _load_accessible_project(ctx)
    response.headers.update(CAROUSEL_PREVIEW_CACHE_HEADERS)
    if project.design_tokens is None:
        raise HTTPException(status_code=404, detail=ERR_DESIGN_NOT_GENERATED)

    tokens = handlers.merge_design_tokens(project)
    layout = dict(tokens["layout"])
    layout["swipe_text"] = _swipe_text_for_language(lang)

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
        theme_name=project.theme,
    )


@router.get(
    "/{project_id}/preview/images/{filename}",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def preview_carousel_image(
    request: Request,
    project_id: UUID,
    filename: Annotated[str, FastPath(pattern=r"^[a-zA-Z0-9_\-\.]+$")],
    user: Annotated[User, Depends(require_authenticated_user)],
    handlers: PresentationHandlersDep,
    lang: Annotated[str, Query(pattern="^(pt|en)$")] = BLOG_LANGUAGE_PT,
) -> FileResponse:
    """Preview draft slide or hero images for authenticated project owners."""
    ctx = PreviewAccessContext(project_id=project_id, user=user, handlers=handlers)
    project = await _load_accessible_project_with_output(ctx)

    lang_dir = Path(project.output_dir or "") / lang
    # Try HD first, then standard, then hero images
    hd_dir = lang_dir / HD_SUBDIR_NAME
    image_path = _resolve_image_file(hd_dir, filename)
    if image_path is None:
        image_path = _resolve_image_file(lang_dir, filename)
    if image_path is None:
        image_path = _resolve_image_file(
            Path(project.output_dir or "") / SHARED_IMAGES_DIR_NAME,
            filename,
        )
    if image_path is None:
        raise HTTPException(status_code=404, detail=ERR_IMAGE_NOT_FOUND)

    return FileResponse(
        path=str(image_path),
        media_type=MEDIA_TYPE_JPEG,
        headers=_PREVIEW_JPEG_CACHE_HEADERS,
    )
