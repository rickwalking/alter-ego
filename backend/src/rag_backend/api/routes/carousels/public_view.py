"""Anonymous public carousel projection (AE-0444).

The public viewer needs slide images + headings for every available language,
but the owner-only ``/slides`` response exposes internal ``image_path`` values
and only one language. This edge builds a lean projection from the presentation
handlers' design-token merge and returns a uniform 404 for anything that is not
published, completed, and generated (ADR-0013).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from rag_backend.api.constants import ERR_CAROUSEL_NOT_FOUND, ERR_NOT_FOUND
from rag_backend.api.dependencies.presentation import get_presentation_handlers
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.carousels.carousel_access import (
    assert_carousel_public_completed,
)
from rag_backend.api.schemas import CarouselPublicResponse, CarouselPublicSlide
from rag_backend.domain.constants import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_CAROUSEL_PUBLISH
from rag_backend.domain.models import CarouselProject, CarouselSlide
from rag_backend.modules.presentation import PresentationHandlers

router = APIRouter()

PresentationHandlersDep = Annotated[
    PresentationHandlers, Depends(get_presentation_handlers)
]

_IMAGE_KEY_HERO = "hero"
_IMAGE_KEY_PT = "rendered_slides_pt"
_IMAGE_KEY_EN = "rendered_slides_en"
_IMAGE_KEY_RAW = "slides"
_SLIDE_NUMBER_PATTERN = re.compile(r"slide_(\d+)")


def _slide_number_from_url(url: str, index: int) -> int:
    match = _SLIDE_NUMBER_PATTERN.search(url)
    return int(match.group(1)) if match else index + 1


def _headings_by_number(slides: Sequence[CarouselSlide]) -> dict[int, str]:
    return {slide.slide_number: slide.heading for slide in slides}


def _public_slides(
    urls: object,
    headings: dict[int, str],
) -> list[CarouselPublicSlide]:
    if not isinstance(urls, list):
        return []
    slides: list[CarouselPublicSlide] = []
    for index, url in enumerate(urls):
        if not isinstance(url, str) or not url:
            continue
        number = _slide_number_from_url(url, index)
        slides.append(
            CarouselPublicSlide(
                slide_number=number,
                heading=headings.get(number),
                image_url=url,
            )
        )
    return slides


def _images(tokens: dict[str, object]) -> dict[str, object]:
    images = tokens.get("images")
    return images if isinstance(images, dict) else {}


def _string_value(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _build_public_response(
    project: CarouselProject,
    slides: Sequence[CarouselSlide],
    tokens: dict[str, object],
) -> CarouselPublicResponse | None:
    images = _images(tokens)
    headings = _headings_by_number(slides)
    portuguese = _public_slides(images.get(_IMAGE_KEY_PT), headings)
    if not portuguese:
        portuguese = _public_slides(images.get(_IMAGE_KEY_RAW), headings)
    english = _public_slides(images.get(_IMAGE_KEY_EN), headings)

    slides_by_language: dict[str, list[CarouselPublicSlide]] = {}
    if portuguese:
        slides_by_language[LANGUAGE_PT] = portuguese
    if english:
        slides_by_language[LANGUAGE_EN] = english
    if not slides_by_language:
        return None

    cover = _string_value(images.get(_IMAGE_KEY_HERO))
    if cover is None:
        first_language = next(iter(slides_by_language.values()))
        cover = first_language[0].image_url

    return CarouselPublicResponse(
        id=project.id,
        title=project.title,
        title_en=project.title_en,
        subtitle=project.subtitle,
        subtitle_en=project.subtitle_en,
        language=project.language,
        created_at=project.created_at,
        slide_count=max(len(portuguese), len(english)),
        available_languages=list(slides_by_language),
        slides_by_language=slides_by_language,
        cover_url=cover,
    )


@router.get(
    "/{project_id}/public",
    responses={404: {"description": ERR_NOT_FOUND}},
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def get_public_carousel(
    request: Request,
    project_id: UUID,
    handlers: PresentationHandlersDep,
) -> CarouselPublicResponse:
    """Return the anonymous viewer projection for a published carousel."""
    project = await handlers.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    assert_carousel_public_completed(project)
    if project.output_dir is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)

    slides = await handlers.get_slides(project_id)
    response = _build_public_response(
        project,
        slides,
        handlers.merge_design_tokens(project),
    )
    if response is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    return response
