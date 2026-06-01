"""Unit tests for editorial carousel finalize/export."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.editorial_finalize import (
    export_and_complete_carousel,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus


@pytest.mark.asyncio
async def test_export_skips_when_output_dir_missing() -> None:
    """Scenario: finalize does not call re_render without output_dir."""
    project_id = uuid4()
    project = CarouselProject(
        id=project_id,
        topic="T",
        audience="A",
        niche="N",
        status=CarouselStatus.DRAFTING,
        output_dir=None,
    )
    mock_repo = MagicMock()
    mock_repo.get_project_by_id = AsyncMock(return_value=project)
    refinement = MagicMock()
    refinement.re_render_slides = AsyncMock()

    with patch(
        "rag_backend.application.services.carousel.editorial_finalize.PostgresCarouselRepository",
        return_value=mock_repo,
    ):
        await export_and_complete_carousel(MagicMock(), refinement, str(project_id))

    refinement.re_render_slides.assert_not_called()


@pytest.mark.asyncio
async def test_export_marks_completed_after_render() -> None:
    """Scenario: successful re_render sets status completed and updates project."""
    project_id = uuid4()
    project = CarouselProject(
        id=project_id,
        topic="T",
        audience="A",
        niche="N",
        status=CarouselStatus.GENERATING_IMAGES,
        output_dir=f"/tmp/{project_id}",
    )
    mock_repo = MagicMock()
    mock_repo.get_project_by_id = AsyncMock(return_value=project)
    mock_repo.update_project = AsyncMock(side_effect=lambda p: p)

    rendered = CarouselProject(
        id=project_id,
        topic="T",
        audience="A",
        niche="N",
        status=CarouselStatus.GENERATING_IMAGES,
        output_dir=project.output_dir,
    )
    refinement = MagicMock()
    refinement.re_render_slides = AsyncMock(return_value=rendered)

    with (
        patch(
            "rag_backend.application.services.carousel.editorial_finalize.PostgresCarouselRepository",
            return_value=mock_repo,
        ),
        patch(
            "rag_backend.application.services.carousel.editorial_finalize._merge_design_tokens_with_disk",
            return_value={
                "images": {
                    "rendered_slides_pt": ["/out/slide_1_pt.png"],
                    "rendered_slides_en": ["/out/slide_1_en.png"],
                },
            },
        ),
    ):
        await export_and_complete_carousel(MagicMock(), refinement, str(project_id))

    assert rendered.status == CarouselStatus.COMPLETED
    mock_repo.update_project.assert_called_once()
    updated_arg = mock_repo.update_project.call_args[0][0]
    images = (updated_arg.design_tokens or {}).get("images", {})
    assert images.get("rendered_slides_en") == ["/out/slide_1_en.png"]
