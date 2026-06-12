"""Authenticated preview routes for draft carousel content."""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.params import Path as FastPath
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import (
    CAROUSEL_PREVIEW_CACHE_HEADERS,
    ERR_CAROUSEL_NOT_FOUND,
    ERR_DESIGN_NOT_GENERATED,
    ERR_FORBIDDEN,
    ERR_IMAGE_NOT_FOUND,
    ERR_NOT_AUTHENTICATED,
    ERR_NOT_FOUND,
    MEDIA_TYPE_JPEG,
)
from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas import (
    CarouselBlogI18nResponse,
    CarouselDesignColors,
    CarouselDesignImages,
    CarouselDesignLayout,
    CarouselDesignResponse,
    CarouselDesignTypography,
)
from rag_backend.application.services.carousel.design_token_utils import (
    merge_design_tokens_with_disk,
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
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

from .deps import get_carousel_repo
from .helpers import (
    _PREVIEW_JPEG_CACHE_HEADERS,
    _extract_first_paragraph,
    _extract_title_and_subtitle,
    _load_project_with_output,
    _resolve_image_file,
    assert_carousel_project_access,
)

router = APIRouter()


@dataclass(frozen=True)
class PreviewAccessContext:
    """Shared dependencies for authenticated carousel preview routes."""

    project_id: UUID
    user: User
    repo: CarouselRepository
    db: AsyncSession


async def _assigned_reviewer_id(
    db: AsyncSession,
    project_id: UUID,
) -> str | None:
    model = await db.get(CarouselProjectModel, str(project_id))
    if model is None:
        return None
    return model.assigned_reviewer_id


async def _load_accessible_project(ctx: PreviewAccessContext) -> CarouselProject:
    project = await ctx.repo.get_project_by_id(ctx.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    assigned_reviewer_id = await _assigned_reviewer_id(ctx.db, ctx.project_id)
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
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
) -> CarouselBlogI18nResponse:
    """Preview draft blog content for authenticated project owners."""
    ctx = PreviewAccessContext(project_id=project_id, user=user, repo=repo, db=db)
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
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
) -> CarouselDesignResponse:
    """Preview draft design tokens for authenticated project owners."""
    ctx = PreviewAccessContext(project_id=project_id, user=user, repo=repo, db=db)
    project = await _load_accessible_project(ctx)
    response.headers.update(CAROUSEL_PREVIEW_CACHE_HEADERS)
    if project.design_tokens is None:
        raise HTTPException(status_code=404, detail=ERR_DESIGN_NOT_GENERATED)

    tokens = merge_design_tokens_with_disk(project)
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
        theme_name=project.theme.value,
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
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    db: Annotated[AsyncSession, Depends(get_db)],
    lang: Annotated[str, Query(pattern="^(pt|en)$")] = BLOG_LANGUAGE_PT,
) -> FileResponse:
    """Preview draft slide or hero images for authenticated project owners."""
    project = await _load_project_with_output(project_id, repo)
    assigned_reviewer_id = await _assigned_reviewer_id(db, project_id)
    assert_carousel_project_access(
        project,
        user,
        assigned_reviewer_id=assigned_reviewer_id,
    )

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
