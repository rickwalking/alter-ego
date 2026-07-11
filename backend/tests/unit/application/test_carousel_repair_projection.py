"""Unit tests for the carousel repair projection mapping (AE-0311).

Gherkin: tests/features/carousel_deterministic_repair.feature
"""

from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

import pytest

from rag_backend.application.services.carousel.carousel_repair_projection import (
    apply_localized_to_slides,
    localized_from_slides,
)
from rag_backend.domain.models.carousel import CarouselSlide
from rag_backend.domain.protocols.repositories import CarouselRepository


class _RecordingRepo:
    """Minimal repo double capturing ``update_slide`` writes."""

    def __init__(self) -> None:
        self.updated: list[CarouselSlide] = []

    async def update_slide(self, slide: CarouselSlide) -> CarouselSlide:
        self.updated.append(slide)
        return slide


def _slide(project_id: UUID, *, heading: str, body: str) -> CarouselSlide:
    return CarouselSlide(
        project_id=project_id,
        slide_number=4,
        slide_type="content",
        heading=heading,
        body=body,
        extras={"translation_en": {"heading": "EN heading", "body": "EN body"}},
    )


class TestLocalizedFromSlides:
    """Projection rows reconstruct canonical localized records."""

    def test_maps_heading_body_and_translation(self) -> None:
        slide = _slide(uuid4(), heading="Titulo", body="Corpo")
        localized = localized_from_slides([slide])
        assert localized[0]["slide_index"] == 4
        assert localized[0]["presentation_pt"]["heading"] == "Titulo"
        assert localized[0]["presentation_pt"]["body"] == "Corpo"
        assert localized[0]["presentation_en"]["heading"] == "EN heading"


class TestApplyLocalizedToSlides:
    """Repaired records are written back to the matching projection rows."""

    @pytest.mark.asyncio
    async def test_overwrites_matching_row_copy(self) -> None:
        repo = _RecordingRepo()
        slide = _slide(uuid4(), heading="old", body="stale")
        repaired = [
            {
                "slide_index": 4,
                "slide_type": "content",
                "presentation_pt": {
                    "slide_type": "content",
                    "heading": "Novo titulo",
                    "body": "Novo corpo limpo.",
                },
                "presentation_en": {
                    "slide_type": "content",
                    "heading": "New title",
                    "body": "New clean body.",
                },
            }
        ]
        updated = await apply_localized_to_slides(
            cast(CarouselRepository, repo), [slide], repaired
        )
        assert updated == (4,)
        assert slide.heading == "Novo titulo"
        assert slide.body == "Novo corpo limpo."
        assert repo.updated == [slide]

    @pytest.mark.asyncio
    async def test_skips_rows_without_a_repaired_record(self) -> None:
        repo = _RecordingRepo()
        slide = _slide(uuid4(), heading="keep", body="keep")
        updated = await apply_localized_to_slides(
            cast(CarouselRepository, repo), [slide], []
        )
        assert updated == ()
        assert repo.updated == []
        assert slide.heading == "keep"
