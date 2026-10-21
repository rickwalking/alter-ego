"""Public carousel viewer projection (AE-0444).

Gherkin: tests/features/public_carousel_view_ae0444.feature
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from rag_backend.api.routes.carousels.public_view import get_public_carousel
from rag_backend.domain.models import CarouselProject, CarouselSlide, CarouselStatus

PROJECT_ID = UUID("0f8fad5b-d9cb-469f-a165-70867728950e")
BASE = f"/api/carousels/{PROJECT_ID}"


def _request() -> Request:
    return Request({
        "type": "http",
        "method": "GET",
        "path": f"{BASE}/public",
        "headers": [],
        "query_string": b"",
        "server": ("test", 80),
        "client": ("127.0.0.1", 12345),
    })


def _project(
    *,
    is_public: bool = True,
    status: CarouselStatus = CarouselStatus.COMPLETED,
    output_dir: str | None = "/tmp/carousel",
) -> CarouselProject:
    return CarouselProject(
        id=PROJECT_ID,
        topic="Public viewer",
        audience="Devs",
        niche="AI",
        title="Título PT",
        title_en="English title",
        subtitle="Subtítulo PT",
        subtitle_en="English subtitle",
        language="pt-BR",
        is_public=is_public,
        status=status,
        output_dir=output_dir,
        created_at=datetime(2026, 10, 20, 11, 40, 1),
    )


def _slides() -> list[CarouselSlide]:
    return [
        CarouselSlide(
            project_id=PROJECT_ID,
            slide_number=1,
            slide_type="intro",
            heading="Abertura",
            body="Corpo",
        ),
        CarouselSlide(
            project_id=PROJECT_ID,
            slide_number=2,
            slide_type="content",
            heading="Segundo",
            body="Corpo",
        ),
    ]


def _tokens(
    *,
    pt: object = None,
    en: object = None,
    raw: object = None,
    hero: object = None,
) -> dict[str, object]:
    images: dict[str, object] = {"slides": raw if raw is not None else []}
    if pt is not None:
        images["rendered_slides_pt"] = pt
    if en is not None:
        images["rendered_slides_en"] = en
    if hero is not None:
        images["hero"] = hero
    return {"images": images}


def _handlers(
    project: CarouselProject | None,
    *,
    slides: list[CarouselSlide] | None = None,
    tokens: dict[str, object] | None = None,
) -> MagicMock:
    handlers = MagicMock()
    handlers.get_project = AsyncMock(return_value=project)
    handlers.get_slides = AsyncMock(return_value=slides or [])
    handlers.merge_design_tokens = MagicMock(
        return_value=tokens or _tokens(pt=[], en=[])
    )
    return handlers


async def _get(handlers: MagicMock):
    return await get_public_carousel(
        request=_request(),
        project_id=PROJECT_ID,
        handlers=handlers,
    )


@pytest.mark.unit
class TestPublicCarouselProjection:
    """Scenarios: the anonymous projection exposes only public slide data."""

    async def test_returns_pt_and_en_slides_with_headings(self) -> None:
        tokens = _tokens(
            pt=[
                f"{BASE}/slide-images/pt/slide_1.jpg",
                f"{BASE}/slide-images/pt/slide_2.jpg",
            ],
            en=[
                f"{BASE}/slide-images/en/slide_1.jpg",
                f"{BASE}/slide-images/en/slide_2.jpg",
            ],
            hero=f"{BASE}/slide-images/pt/slide_1.jpg",
        )

        response = await _get(_handlers(_project(), slides=_slides(), tokens=tokens))

        assert response.title == "Título PT"
        assert response.title_en == "English title"
        assert response.language == "pt-BR"
        assert response.slide_count == 2
        assert response.available_languages == ["pt", "en"]
        assert response.cover_url == f"{BASE}/slide-images/pt/slide_1.jpg"
        assert [s.heading for s in response.slides_by_language["pt"]] == [
            "Abertura",
            "Segundo",
        ]
        assert response.slides_by_language["en"][1].slide_number == 2

    async def test_falls_back_to_raw_slides_when_pt_is_missing(self) -> None:
        tokens = _tokens(
            raw=[
                f"{BASE}/images/slide_1.jpg",
                f"{BASE}/images/slide_2.jpg",
            ],
        )

        response = await _get(_handlers(_project(), slides=_slides(), tokens=tokens))

        assert response.available_languages == ["pt"]
        assert response.slides_by_language["pt"][0].image_url == (
            f"{BASE}/images/slide_1.jpg"
        )
        assert response.cover_url == f"{BASE}/images/slide_1.jpg"

    async def test_only_pt_reports_one_language(self) -> None:
        tokens = _tokens(pt=[f"{BASE}/slide-images/pt/slide_1.jpg"])

        response = await _get(_handlers(_project(), slides=_slides(), tokens=tokens))

        assert response.available_languages == ["pt"]
        assert "en" not in response.slides_by_language
        assert response.slide_count == 1

    async def test_ignores_blank_and_non_string_urls(self) -> None:
        tokens = _tokens(pt=["", 42, f"{BASE}/slide-images/pt/slide_2.jpg"])

        response = await _get(_handlers(_project(), slides=_slides(), tokens=tokens))

        slides = response.slides_by_language["pt"]
        assert len(slides) == 1
        assert slides[0].slide_number == 2
        assert slides[0].heading == "Segundo"

    async def test_url_without_slide_number_uses_position(self) -> None:
        tokens = _tokens(pt=[f"{BASE}/slide-images/pt/cover.jpg"])

        response = await _get(_handlers(_project(), slides=_slides(), tokens=tokens))

        assert response.slides_by_language["pt"][0].slide_number == 1
        assert response.slides_by_language["pt"][0].heading == "Abertura"

    async def test_missing_headings_are_null(self) -> None:
        tokens = _tokens(pt=[f"{BASE}/slide-images/pt/slide_1.jpg"])

        response = await _get(_handlers(_project(), slides=[], tokens=tokens))

        assert response.slides_by_language["pt"][0].heading is None


@pytest.mark.unit
class TestPublicCarouselAccess:
    """Scenarios: private, non-completed, unknown, or empty carousels are 404."""

    async def test_unknown_carousel_is_404(self) -> None:
        with pytest.raises(HTTPException) as exc:
            await _get(_handlers(None))

        assert exc.value.status_code == 404

    async def test_private_carousel_is_404(self) -> None:
        project = _project(is_public=False)
        tokens = _tokens(pt=[f"{BASE}/slide-images/pt/slide_1.jpg"])

        with pytest.raises(HTTPException) as exc:
            await _get(_handlers(project, tokens=tokens))

        assert exc.value.status_code == 404

    async def test_non_completed_carousel_is_404(self) -> None:
        project = _project(status=CarouselStatus.PENDING)
        tokens = _tokens(pt=[f"{BASE}/slide-images/pt/slide_1.jpg"])

        with pytest.raises(HTTPException) as exc:
            await _get(_handlers(project, tokens=tokens))

        assert exc.value.status_code == 404

    async def test_carousel_without_output_is_404(self) -> None:
        project = _project(output_dir=None)
        tokens = _tokens(pt=[f"{BASE}/slide-images/pt/slide_1.jpg"])

        with pytest.raises(HTTPException) as exc:
            await _get(_handlers(project, tokens=tokens))

        assert exc.value.status_code == 404

    async def test_carousel_without_images_is_404(self) -> None:
        tokens = _tokens(pt=[], en=[])

        with pytest.raises(HTTPException) as exc:
            await _get(_handlers(_project(), slides=_slides(), tokens=tokens))

        assert exc.value.status_code == 404
