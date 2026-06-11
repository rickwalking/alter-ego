"""Shared helpers for carousel refinement tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from rag_backend.application.services.carousel.refinement_service import (
    CarouselRefinementConfig,
    CarouselRefinementService,
)
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.domain.models import CarouselSlide


def make_test_slide(
    number: int, extras: dict[str, object] | None = None
) -> CarouselSlide:
    return CarouselSlide(
        project_id=uuid4(),
        slide_number=number,
        slide_type="content",
        heading=f"Heading {number}",
        body=f"Body {number}",
        image_prompt="A scene",
        extras=extras,
    )


def make_refinement_service_with_mocks() -> tuple[
    CarouselRefinementService, AsyncMock, AsyncMock, MagicMock
]:
    repo = AsyncMock()
    repo.update_project = AsyncMock(side_effect=lambda p: p)
    repo.get_slides_by_project = AsyncMock()
    export = AsyncMock()
    export.export_slides = AsyncMock(
        return_value=["/tmp/slide_1.jpg", "/tmp/slide_2.jpg"]
    )
    pdf_builder = MagicMock()
    pdf_builder.build = MagicMock(return_value="/tmp/carousel.pdf")
    image_service = AsyncMock()
    registry = ImageProviderRegistry(
        gemini_service=image_service, openai_service=image_service
    )
    agent = CarouselRefinementService(
        CarouselRefinementConfig(
            repository=repo,
            llm_service=AsyncMock(),
            image_registry=registry,
            export_service=export,
            pdf_slide_builder=pdf_builder,
        )
    )
    return agent, repo, export, pdf_builder
