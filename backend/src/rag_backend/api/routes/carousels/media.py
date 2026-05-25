from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.params import Path as FastPath
from fastapi.responses import FileResponse

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
    ERR_PDF_FILE_MISSING,
    ERR_PDF_NOT_GENERATED,
    MEDIA_TYPE_JPEG,
    MEDIA_TYPE_PDF,
)
from rag_backend.api.dependencies import (
    get_optional_user,
    require_authenticated_user,
)
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
from rag_backend.domain.models import User
from rag_backend.domain.protocols import CarouselRepository

from .deps import get_carousel_repo
from .helpers import (
    _JPEG_CACHE_HEADERS,
    _build_default_design_tokens,
    _extract_first_paragraph,
    _extract_title_and_subtitle,
    _load_project_with_output,
    _pdf_path_for_language,
    _resolve_image_file,
)

router = APIRouter()


@router.get(
    "/{project_id}/pdf",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
    },
)
async def get_carousel_pdf(
    project_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    lang: Annotated[str, Query(pattern="^(pt|en)$")] = "pt",
) -> FileResponse:
    """Stream the carousel.pdf file for LinkedIn document posting."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    target_path = _pdf_path_for_language(project, lang)
    if not target_path:
        raise HTTPException(status_code=404, detail=ERR_PDF_NOT_GENERATED)
    pdf_file = Path(target_path)
    if not pdf_file.exists():
        raise HTTPException(status_code=404, detail=ERR_PDF_FILE_MISSING)
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
async def get_carousel_blog(
    project_id: UUID,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselBlogResponse:
    """Get the generated blog post for a carousel (default pt-BR)."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    if project.blog_markdown is None:
        raise HTTPException(status_code=404, detail=ERR_BLOG_NOT_GENERATED)
    return CarouselBlogResponse(
        markdown=project.blog_markdown,
        title=project.title or project.topic,
        subtitle=project.subtitle,
    )


@router.get(
    "/{project_id}/blog/{lang}",
    responses={
        404: {"description": ERR_NOT_FOUND},
    },
)
async def get_carousel_blog_i18n(
    project_id: UUID,
    lang: Annotated[str, FastPath(pattern="^(pt|en)$")],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselBlogI18nResponse:
    """Get the generated blog post in a specific language."""

    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)

    blog_content = project.get_blog(lang)
    if blog_content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Blog post not available in '{lang}'",
            headers={"X-Available-Languages": ",".join(project.get_available_languages())},
        )

    translated_title, translated_subtitle = _extract_title_and_subtitle(blog_content)

    if lang == "en":
        title = translated_title or project.title_en or project.title or project.topic
        subtitle = (
            translated_subtitle
            or project.subtitle_en
            or _extract_first_paragraph(blog_content)
            or project.subtitle
        )
    else:
        title = translated_title or project.title or project.topic
        subtitle = translated_subtitle or project.subtitle

    return CarouselBlogI18nResponse(
        markdown=blog_content,
        title=title,
        subtitle=subtitle,
        language=lang,
        available_languages=project.get_available_languages(),
    )


@router.get(
    "/{project_id}/design",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        404: {"description": ERR_NOT_FOUND},
    },
)
async def get_carousel_design(
    project_id: UUID,
    user: Annotated[User | None, Depends(get_optional_user)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    lang: Annotated[str, Query(pattern="^(pt|en)$")] = "pt",
) -> CarouselDesignResponse:
    """Get the visual design tokens for a carousel."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    if project.design_tokens is None:
        raise HTTPException(status_code=404, detail=ERR_DESIGN_NOT_GENERATED)

    raw_tokens = project.design_tokens
    theme_name = project.theme.value

    required_keys = ("colors", "typography", "images", "layout")
    defaults = _build_default_design_tokens(project)
    if not raw_tokens or not all(k in raw_tokens for k in required_keys):
        tokens: dict[str, object] = defaults
    else:
        raw_images = dict(raw_tokens.get("images", {}))
        default_images = defaults["images"]
        merged_images = {
            **default_images,
            **raw_images,
        }
        tokens = {
            **defaults,
            **raw_tokens,
            "images": merged_images,
        }

    layout = dict(tokens["layout"])
    layout["swipe_text"] = "Swipe \u2192" if lang == "en" else "Deslize \u2192"

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
async def get_carousel_image(
    project_id: UUID,
    filename: str,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> FileResponse:
    """Serve a raw hero image (from <output>/images/)."""
    project = await _load_project_with_output(project_id, repo)
    image_path = _resolve_image_file(Path(project.output_dir or "") / "images", filename)
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
async def get_carousel_slides(
    project_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> list[CarouselSlideResponse]:
    """Get all slides for a carousel project."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    slides = await repo.get_slides_by_project(project_id)
    return [CarouselSlideResponse.model_validate(s) for s in slides]


@router.get(
    "/{project_id}/download",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
    },
)
async def download_carousel(
    project_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> dict[str, str]:
    """Get download info for carousel files."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    if project.output_dir is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_GENERATED)
    output_path = Path(project.output_dir)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail=ERR_OUTPUT_NOT_FOUND)
    files = [str(p.relative_to(output_path)) for p in output_path.rglob("*") if p.is_file()]
    return {"output_dir": project.output_dir, "files": files}
