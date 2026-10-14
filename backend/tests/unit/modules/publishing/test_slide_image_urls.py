"""Public slide URLs stay byte-identical to the Instagram route helper."""

from __future__ import annotations

from uuid import UUID

from rag_backend.api.routes.carousels.helpers import _build_public_image_urls
from rag_backend.domain.constants import LANGUAGE_PT
from rag_backend.modules.publishing.application.slide_image_urls import (
    SlideImageUrlRequest,
    build_public_slide_image_urls,
)

_PROJECT = UUID("550e8400-e29b-41d4-a716-446655440000")


def test_slide_urls_match_the_historical_template(monkeypatch) -> None:
    monkeypatch.setenv("CAROUSEL_PUBLIC_BASE_URL", "https://public.test/")
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    expected = build_public_slide_image_urls(
        SlideImageUrlRequest(
            base_url="https://public.test",
            project_id=str(_PROJECT),
            slide_numbers=(1, 2),
            language=LANGUAGE_PT,
        )
    )
    assert expected == [
        f"https://public.test/api/carousels/{_PROJECT}/slide-images/pt/slide_1.jpg",
        f"https://public.test/api/carousels/{_PROJECT}/slide-images/pt/slide_2.jpg",
    ]
    assert _build_public_image_urls(_PROJECT, [1, 2]) == expected
    get_settings.cache_clear()
