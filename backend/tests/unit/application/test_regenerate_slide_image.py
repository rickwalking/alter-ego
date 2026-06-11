"""Unit tests for CarouselRefinementService.regenerate_slide_image.

Gherkin:
  tests/features/carousel_image_refinement.feature
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from rag_backend.domain.models import (
    CarouselProject,
    CarouselStatus,
)

from .carousel_refinement_helpers import (
    make_refinement_service_with_mocks,
    make_test_slide,
)


@pytest.mark.unit
class TestRegenerateSlideImage:
    """The image regeneration flow."""

    # Scenario: Regenerate image with a new prompt
    @patch("rag_backend.application.services.carousel_refinement.run_image_one")
    async def test_regenerate_image_rewrites_prompt_and_exports(
        self, mock_run_image_one: AsyncMock, tmp_path: Path
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
        slide = make_test_slide(2, extras={"image_prompt": "old scene"})
        repo.get_slides_by_project = AsyncMock(return_value=[make_test_slide(1), slide])
        agent._llm.generate = AsyncMock(return_value="new futuristic scene")

        result = await agent.regenerate_slide_image(project.id, 2, "make it futuristic")

        assert all(
            call.args[0] == project.id
            for call in repo.get_project_by_id.await_args_list
        )
        assert all(
            call.args[0] == project.id
            for call in repo.get_slides_by_project.await_args_list
        )
        llm_messages = agent._llm.generate.call_args[0][0]
        rewrite_prompt = llm_messages[0]["content"]
        assert llm_messages[0]["role"] == "user"
        assert agent._llm.generate.call_args.kwargs["temperature"] == 0.7
        assert "make it futuristic" in rewrite_prompt
        assert "A scene" in rewrite_prompt
        assert slide.image_prompt == "new futuristic scene"
        assert slide.extras is not None
        assert slide.extras.get("image_prompt") == "new futuristic scene"
        repo.update_slide.assert_awaited_once_with(slide)
        mock_run_image_one.assert_awaited_once()
        config_arg = mock_run_image_one.call_args.args[0]
        assert config_arg.slide.image_prompt == "new futuristic scene"
        assert export.export_slides.await_count >= 1
        pdf_builder.build.assert_called_once()
        assert result.id == project.id

    # Scenario: Missing project is rejected during image regeneration
    async def test_regenerate_raises_when_project_missing(self) -> None:
        agent, repo, _, _ = make_refinement_service_with_mocks()
        missing_id = uuid4()
        repo.get_project_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match=str(missing_id)):
            await agent.regenerate_slide_image(missing_id, 1, "change colors")

    # Scenario: Missing output_dir is rejected during image regeneration
    async def test_regenerate_raises_when_no_output_dir(self) -> None:
        agent, repo, _, _ = make_refinement_service_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=None,
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        with pytest.raises(ValueError, match=str(project.id)):
            await agent.regenerate_slide_image(project.id, 1, "change colors")

    # Scenario: Missing slide is rejected during image regeneration
    async def test_regenerate_raises_when_slide_missing(self) -> None:
        agent, repo, _, _ = make_refinement_service_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir="/tmp/x",
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[make_test_slide(1)])
        with pytest.raises(ValueError, match=f"Slide 2 not found.*{project.id}"):
            await agent.regenerate_slide_image(project.id, 2, "change colors")

    # Scenario: Empty LLM response is rejected during image regeneration
    @patch("rag_backend.application.services.carousel_refinement.run_image_one")
    async def test_regenerate_raises_when_llm_returns_empty_prompt(
        self, _mock_run_image_one: AsyncMock, tmp_path: Path
    ) -> None:
        agent, repo, _, _ = make_refinement_service_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        slide = make_test_slide(1, extras={"image_prompt": "old scene"})
        repo.get_slides_by_project = AsyncMock(return_value=[slide])
        agent._llm.generate = AsyncMock(return_value="   ")

        with pytest.raises(ValueError, match="empty image prompt"):
            await agent.regenerate_slide_image(project.id, 1, "make it brighter")

    # Scenario: Missing image_prompt is rejected during image regeneration
    async def test_regenerate_raises_when_no_image_prompt(self) -> None:
        agent, repo, _, _ = make_refinement_service_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir="/tmp/x",
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        slide = make_test_slide(1)
        slide.image_prompt = None
        slide.extras = None
        repo.get_slides_by_project = AsyncMock(return_value=[slide])
        with pytest.raises(ValueError, match="no image_prompt"):
            await agent.regenerate_slide_image(project.id, 1, "change colors")
