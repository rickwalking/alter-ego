"""Unit tests for CarouselRefinementService.refine_carousel_design.

Gherkin:
  tests/features/carousel_design_refinement.feature
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
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
class TestRefineCarouselDesign:
    """The design refinement flow."""

    # Scenario: Apply a CSS override and re-export
    async def test_refinement_writes_css_and_re_exports(self, tmp_path: Path) -> None:
        agent, repo, export, pdf_builder = make_refinement_service_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(
            return_value=[make_test_slide(1), make_test_slide(2)]
        )
        agent._phase4_design = MagicMock(
            return_value="<html><style>.hero-img { height: 400px; }</style></html>"
        )
        agent._llm.generate = AsyncMock(return_value=".hero-img { height: 500px; }")

        result = await agent.refine_carousel_design(project.id, "make images bigger")

        assert all(
            call.args[0] == project.id
            for call in repo.get_project_by_id.await_args_list
        )
        assert all(
            call.args[0] == project.id
            for call in repo.get_slides_by_project.await_args_list
        )
        llm_messages = agent._llm.generate.call_args[0][0]
        design_prompt = llm_messages[0]["content"]
        assert llm_messages[0]["role"] == "user"
        assert agent._llm.generate.call_args.kwargs["temperature"] == 0.3
        assert "make images bigger" in design_prompt
        assert ".hero-img { height: 400px; }" in design_prompt
        overrides_file = tmp_path / "design_overrides.css"
        assert overrides_file.exists()
        assert ".hero-img { height: 500px; }" in overrides_file.read_text()
        assert export.export_slides.await_count >= 1
        pdf_builder.build.assert_called_once()
        assert result.id == project.id

    async def test_refinement_extracts_first_style_block_from_html(
        self, tmp_path: Path
    ) -> None:
        """Given multiple style blocks, when refining, then first CSS block is used."""
        agent, repo, _, _ = make_refinement_service_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[make_test_slide(1)])
        agent._phase4_design = MagicMock(
            return_value=(
                "<html><style>.legacy { color: red; }</style>"
                "<style>.hero-img { height: 400px; }</style></html>"
            )
        )
        agent._llm.generate = AsyncMock(return_value=".legacy { color: blue; }")

        await agent.refine_carousel_design(project.id, "recolor legacy")

        design_prompt = agent._llm.generate.call_args[0][0][0]["content"]
        assert ".legacy { color: red; }" in design_prompt
        assert ".hero-img { height: 400px; }" not in design_prompt

    async def test_refinement_uses_empty_css_when_html_has_no_style_block(
        self, tmp_path: Path
    ) -> None:
        """Given HTML without style tags, when refining, then prompt still renders."""
        agent, repo, _, _ = make_refinement_service_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[make_test_slide(1)])
        agent._phase4_design = MagicMock(
            return_value="<html><body>No CSS</body></html>"
        )
        agent._llm.generate = AsyncMock(return_value=".hero-img { width: 100%; }")

        await agent.refine_carousel_design(project.id, "widen images")

        design_prompt = agent._llm.generate.call_args[0][0][0]["content"]
        assert "widen images" in design_prompt
        assert "Existing CSS classes" in design_prompt

    async def test_refinement_raises_when_overrides_file_cannot_be_written(
        self, tmp_path: Path
    ) -> None:
        """Given write failure, when refining, then error includes overrides path."""
        agent, repo, _, _ = make_refinement_service_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[make_test_slide(1)])
        agent._phase4_design = MagicMock(
            return_value="<html><style>.x{}</style></html>"
        )
        agent._llm.generate = AsyncMock(return_value=".hero-img { opacity: 1; }")
        overrides_path = tmp_path / "design_overrides.css"

        with (
            patch.object(Path, "write_text", side_effect=OSError("permission denied")),
            pytest.raises(ValueError, match=str(overrides_path)),
        ):
            await agent.refine_carousel_design(project.id, "adjust opacity")

    # Scenario: Markdown fences are stripped from LLM output
    async def test_refinement_strips_markdown_fences(self, tmp_path: Path) -> None:
        agent, repo, export, _ = make_refinement_service_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[make_test_slide(1)])
        agent._llm.generate = AsyncMock(
            return_value="```css\n.hero-img { height: 600px; }\n```"
        )

        await agent.refine_carousel_design(project.id, "make images bigger")

        overrides_file = tmp_path / "design_overrides.css"
        content = overrides_file.read_text()
        assert "```" not in content
        assert ".hero-img { height: 600px; }" in content

    # Scenario: Empty LLM CSS response is rejected during design refinement
    async def test_refinement_raises_when_llm_returns_empty_css(
        self, tmp_path: Path
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
        repo.get_slides_by_project = AsyncMock(return_value=[make_test_slide(1)])
        agent._llm.generate = AsyncMock(return_value="  ")

        with pytest.raises(ValueError, match="empty CSS"):
            await agent.refine_carousel_design(project.id, "make images bigger")

    # Scenario: Missing project is rejected during design refinement
    async def test_refinement_raises_when_project_missing(self) -> None:
        agent, repo, _, _ = make_refinement_service_with_mocks()
        missing_id = uuid4()
        repo.get_project_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match=str(missing_id)):
            await agent.refine_carousel_design(missing_id, "change layout")

    # Scenario: Missing output_dir is rejected during design refinement
    async def test_refinement_raises_when_no_output_dir(self) -> None:
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
            await agent.refine_carousel_design(project.id, "change layout")

    # Scenario: No slides is rejected during design refinement
    async def test_refinement_raises_when_no_slides(self) -> None:
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
        with pytest.raises(ValueError, match=str(project.id)):
            await agent.refine_carousel_design(project.id, "change layout")
