"""Unit tests for CarouselRefinementService.re_render_slides + unpack_extras helpers.

Gherkin:
  tests/features/carousel_image_refinement.feature
  tests/features/carousel_design_refinement.feature
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.types import (
    SlideData,
    pack_extras,
    unpack_extras,
)
from rag_backend.domain.models import (
    CarouselProject,
    CarouselStatus,
)

from .carousel_refinement_helpers import (
    make_refinement_service_with_mocks,
    make_test_slide,
)


@pytest.mark.unit
class TestExtrasRoundTrip:
    """Pack and unpack should preserve the structured render cards."""

    # Scenario: Pack extras preserves structured render cards
    def test_pack_includes_features_stats_insight(self) -> None:
        sd = SlideData(
            slide_number=2,
            slide_type="content",
            heading="H",
            body="B",
            image_prompt="scene",
            features=[{"icon": "🧠", "title": "T", "body": "B"}],
            stats=[{"value": "80%", "label": "L", "detail": ""}],
            insight={"quote": "Q", "attribution": "A"},
        )
        packed = pack_extras(sd)
        assert packed is not None
        assert packed["features"] == sd.features
        assert packed["stats"] == sd.stats
        assert packed["insight"] == sd.insight
        assert packed["image_prompt"] == "scene"

    # Scenario: Pack returns None when no optional fields are present
    def test_pack_returns_none_when_empty(self) -> None:
        sd = SlideData(slide_number=1, slide_type="intro", heading="H", body="B")
        assert pack_extras(sd) is None

    # Scenario: Unpack restores features from a DB slide with extras
    def test_unpack_restores_features_from_db_slide(self) -> None:
        slide = make_test_slide(
            3,
            extras={
                "features": [{"icon": "📝", "title": "T", "body": "B"}],
                "stats": None,
                "insight": None,
                "image_prompt": "scene from extras",
            },
        )
        slide.image_prompt = None  # ensure unpack falls back to extras
        sd = unpack_extras(slide)
        assert sd.features == [{"icon": "📝", "title": "T", "body": "B"}]
        assert sd.image_prompt == "scene from extras"
        assert sd.heading == "Heading 3"


@pytest.mark.unit
class TestReRenderSlides:
    """The refine flow's re-render entry point."""

    # Scenario: Re-render writes PDF and bumps updated_at after text edits
    async def test_re_render_writes_pdf_and_bumps_updated_at(
        self, tmp_path: Path
    ) -> None:
        agent, repo, export, pdf_builder = make_refinement_service_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        slides = [make_test_slide(1), make_test_slide(2)]
        repo.get_slides_by_project = AsyncMock(return_value=slides)
        original_updated_at = project.updated_at

        result = await agent.re_render_slides(project.id)

        assert export.export_slides.await_count >= 1
        pdf_builder.build.assert_called_once()
        assert result.pdf_path == "/tmp/carousel.pdf"
        assert result.updated_at != original_updated_at
        repo.update_project.assert_awaited()

    # Scenario: Missing project is rejected during re-render
    async def test_re_render_raises_when_project_missing(self) -> None:
        agent, repo, _, _ = make_refinement_service_with_mocks()
        repo.get_project_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await agent.re_render_slides(uuid4())

    # Scenario: Missing output_dir is rejected during re-render
    async def test_re_render_raises_when_no_output_dir(self) -> None:
        agent, repo, _, _ = make_refinement_service_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=None,
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        with pytest.raises(ValueError, match="output_dir"):
            await agent.re_render_slides(project.id)

    # Scenario: No slides is rejected during re-render
    async def test_re_render_raises_when_no_slides(self) -> None:
        agent, repo, _, _ = make_refinement_service_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir="/tmp/x",
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[])
        with pytest.raises(ValueError, match="no slides"):
            await agent.re_render_slides(project.id)
