"""Public carousel images for anonymous visitors (QA B08).

Gherkin: tests/features/public_carousel_images_ae0412.feature
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from rag_backend.api.routes.carousels.media import get_carousel_image
from rag_backend.application.services.carousel.design_token_utils import (
    merge_design_tokens_with_disk,
)
from rag_backend.domain.models import CarouselProject, CarouselTheme

PROJECT_ID = UUID("64f13017-06ff-4ec1-b1a1-b85ea2d9478a")
BASE = f"/api/carousels/{PROJECT_ID}"


def _project(tmp_path: Path, *, is_public: bool, tokens: dict | None = None):
    return CarouselProject(
        id=PROJECT_ID,
        topic="Test",
        audience="Devs",
        niche="Tech",
        theme=CarouselTheme.CYBERSECURITY,
        output_dir=str(tmp_path),
        is_public=is_public,
        design_tokens=tokens,
    )


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _request() -> Request:
    return Request({
        "type": "http",
        "method": "GET",
        "path": f"{BASE}/images/slide_1.jpg",
        "headers": [],
        "query_string": b"",
        "server": ("test", 80),
        "client": ("127.0.0.1", 12345),
    })


async def _get_image(project: CarouselProject, filename: str, lang: str = "pt"):
    handlers = MagicMock()
    handlers.get_project = AsyncMock(return_value=project)
    return await get_carousel_image(
        request=_request(),
        project_id=project.id,
        filename=filename,
        handlers=handlers,
        lang=lang,
    )


@pytest.mark.unit
class TestPublicDesignTokenImages:
    """Scenarios: preview URLs never leak into a public carousel's tokens."""

    # Scenario: A public carousel never exposes preview image URLs
    def test_public_project_maps_preview_urls_to_public_route(
        self, tmp_path: Path
    ) -> None:
        for i in (1, 2):
            _write(tmp_path / "pt" / f"slide_{i}.jpg", "pt")
        preview = [f"{BASE}/preview/images/slide_{i}.jpg?lang=en" for i in (1, 2, 3)]
        project = _project(
            tmp_path,
            is_public=True,
            tokens={
                "images": {
                    "hero": f"{BASE}/preview/images/slide_1.jpg?lang=pt",
                    "rendered_slides_pt": preview,
                },
            },
        )

        merged = merge_design_tokens_with_disk(project)

        images = merged["images"]
        assert images["hero"] == f"{BASE}/images/slide_1.jpg?lang=pt"
        assert images["rendered_slides_pt"] == [
            f"{BASE}/images/slide_{i}.jpg?lang=en" for i in (1, 2, 3)
        ]
        flat = [images["hero"], *images["slides"], *images["rendered_slides_pt"]]
        assert all("/preview/" not in url for url in flat)

    # Scenario: A preview URL without a language maps to Portuguese
    def test_preview_url_without_lang_maps_to_pt(self, tmp_path: Path) -> None:
        project = _project(
            tmp_path,
            is_public=True,
            tokens={"images": {"hero": f"{BASE}/preview/images/hero.jpg"}},
        )

        merged = merge_design_tokens_with_disk(project)

        assert merged["images"]["hero"] == f"{BASE}/images/hero.jpg?lang=pt"

    def test_public_urls_and_non_strings_are_left_alone(self, tmp_path: Path) -> None:
        project = _project(
            tmp_path,
            is_public=True,
            tokens={
                "images": {
                    "hero": f"{BASE}/images/slide_1",
                    "rendered_slides_pt": [f"{BASE}/slide-images/pt/slide_1.jpg"],
                    "rendered_slides_en": None,
                },
            },
        )

        merged = merge_design_tokens_with_disk(project)

        assert merged["images"]["hero"] == f"{BASE}/images/slide_1"

    def test_public_project_without_output_dir_still_maps(self) -> None:
        project = CarouselProject(
            id=PROJECT_ID,
            topic="Test",
            audience="Devs",
            niche="Tech",
            is_public=True,
            design_tokens={
                "images": {"hero": f"{BASE}/preview/images/slide_1.jpg?lang=en"},
            },
        )

        merged = merge_design_tokens_with_disk(project)

        assert merged["images"]["hero"] == f"{BASE}/images/slide_1.jpg?lang=en"

    # Scenario: Draft carousels keep owner-only preview URLs
    def test_draft_project_keeps_preview_urls(self, tmp_path: Path) -> None:
        _write(tmp_path / "pt" / "slide_1.jpg", "pt")
        project = _project(tmp_path, is_public=False, tokens={"images": {}})

        merged = merge_design_tokens_with_disk(project)

        assert merged["images"]["hero"] == f"{BASE}/preview/images/slide_1.jpg?lang=pt"


@pytest.mark.unit
class TestPublicImageRoute:
    """Scenarios: GET /images/{filename} falls back like the preview route."""

    # Scenario: Public image route serves the raw image first
    async def test_serves_raw_image_first(self, tmp_path: Path) -> None:
        raw = _write(tmp_path / "images" / "slide_1.jpg", "raw")
        _write(tmp_path / "pt" / "slide_1.jpg", "rendered")

        response = await _get_image(_project(tmp_path, is_public=True), "slide_1.jpg")

        assert response.path == str(raw.resolve())

    # Scenario: Public image route falls back to the rendered slide of the language
    async def test_falls_back_to_rendered_slide_of_lang(self, tmp_path: Path) -> None:
        _write(tmp_path / "pt" / "slide_1.jpg", "pt")
        en = _write(tmp_path / "en" / "slide_1.jpg", "en")

        response = await _get_image(
            _project(tmp_path, is_public=True), "slide_1.jpg", lang="en"
        )

        assert response.path == str(en.resolve())

    # Scenario: Public image route falls back to the HD rendered slide
    async def test_falls_back_to_hd_slide(self, tmp_path: Path) -> None:
        hd = _write(tmp_path / "pt" / "hd" / "slide_1.jpg", "hd")

        response = await _get_image(_project(tmp_path, is_public=True), "slide_1")

        assert response.path == str(hd.resolve())

    # Scenario: Missing image still returns 404
    async def test_missing_image_returns_404(self, tmp_path: Path) -> None:
        _write(tmp_path / "pt" / "slide_1.jpg", "pt")

        with pytest.raises(HTTPException) as exc:
            await _get_image(_project(tmp_path, is_public=True), "slide_9.jpg")

        assert exc.value.status_code == 404

    async def test_traversal_filename_is_not_served(self, tmp_path: Path) -> None:
        _write(tmp_path / "secret.jpg", "secret")

        with pytest.raises(HTTPException) as exc:
            await _get_image(_project(tmp_path, is_public=True), "../secret.jpg")

        assert exc.value.status_code == 404

    # Scenario: Draft carousel images stay private
    async def test_draft_carousel_is_not_served(self, tmp_path: Path) -> None:
        _write(tmp_path / "pt" / "slide_1.jpg", "pt")

        with pytest.raises(HTTPException) as exc:
            await _get_image(_project(tmp_path, is_public=False), "slide_1.jpg")

        assert exc.value.status_code != 200
