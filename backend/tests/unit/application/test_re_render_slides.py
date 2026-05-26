"""Unit tests for CarouselAgent.re_render_slides + unpack_extras helpers.

Gherkin:
  tests/features/carousel_image_refinement.feature
  tests/features/carousel_design_refinement.feature
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.types import (
    SlideData,
    pack_extras,
    unpack_extras,
)
from rag_backend.application.services.carousel_agent import CarouselAgent
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
)


def _slide(number: int, extras: dict[str, object] | None = None) -> CarouselSlide:
    return CarouselSlide(
        project_id=uuid4(),
        slide_number=number,
        slide_type="content",
        heading=f"Heading {number}",
        body=f"Body {number}",
        image_prompt="A scene",
        extras=extras,
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
        slide = _slide(
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


def _agent_with_mocks() -> tuple[CarouselAgent, AsyncMock, AsyncMock, MagicMock]:
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
    agent = CarouselAgent(
        repository=repo,
        llm_service=AsyncMock(),
        research_tool=AsyncMock(),
        image_registry=registry,
        export_service=export,
        pdf_slide_builder=pdf_builder,
        output_base_dir="/tmp",
    )
    return agent, repo, export, pdf_builder


@pytest.mark.unit
class TestReRenderSlides:
    """The refine flow's re-render entry point."""

    # Scenario: Re-render writes PDF and bumps updated_at after text edits
    async def test_re_render_writes_pdf_and_bumps_updated_at(
        self, tmp_path: Path
    ) -> None:
        agent, repo, export, pdf_builder = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        slides = [_slide(1), _slide(2)]
        repo.get_slides_by_project = AsyncMock(return_value=slides)
        original_updated_at = project.updated_at

        result = await agent.re_render_slides(project.id)

        export.export_slides.assert_awaited_once()
        pdf_builder.build.assert_called_once()
        assert result.pdf_path == "/tmp/carousel.pdf"
        assert result.updated_at != original_updated_at
        repo.update_project.assert_awaited()

    # Scenario: Missing project is rejected during re-render
    async def test_re_render_raises_when_project_missing(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
        repo.get_project_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await agent.re_render_slides(uuid4())

    # Scenario: Missing output_dir is rejected during re-render
    async def test_re_render_raises_when_no_output_dir(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
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
        agent, repo, _, _ = _agent_with_mocks()
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


@pytest.mark.unit
class TestRegenerateSlideImage:
    """The image regeneration flow."""

    # Scenario: Regenerate image with a new prompt
    @patch("rag_backend.application.services.carousel_refinement.run_image_one")
    async def test_regenerate_image_rewrites_prompt_and_exports(
        self, mock_run_image_one: AsyncMock, tmp_path: Path
    ) -> None:
        agent, repo, export, pdf_builder = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        slide = _slide(2, extras={"image_prompt": "old scene"})
        repo.get_slides_by_project = AsyncMock(return_value=[_slide(1), slide])
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
        slide_arg = mock_run_image_one.call_args.args[1]
        assert slide_arg.image_prompt == "new futuristic scene"
        export.export_slides.assert_awaited_once()
        pdf_builder.build.assert_called_once()
        assert result.id == project.id

    # Scenario: Missing project is rejected during image regeneration
    async def test_regenerate_raises_when_project_missing(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
        missing_id = uuid4()
        repo.get_project_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match=str(missing_id)):
            await agent.regenerate_slide_image(missing_id, 1, "change colors")

    # Scenario: Missing output_dir is rejected during image regeneration
    async def test_regenerate_raises_when_no_output_dir(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
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
        agent, repo, _, _ = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir="/tmp/x",
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[_slide(1)])
        with pytest.raises(ValueError, match=f"Slide 2 not found.*{project.id}"):
            await agent.regenerate_slide_image(project.id, 2, "change colors")

    # Scenario: Empty LLM response is rejected during image regeneration
    @patch("rag_backend.application.services.carousel_refinement.run_image_one")
    async def test_regenerate_raises_when_llm_returns_empty_prompt(
        self, _mock_run_image_one: AsyncMock, tmp_path: Path
    ) -> None:
        agent, repo, _, _ = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        slide = _slide(1, extras={"image_prompt": "old scene"})
        repo.get_slides_by_project = AsyncMock(return_value=[slide])
        agent._llm.generate = AsyncMock(return_value="   ")

        with pytest.raises(ValueError, match="empty image prompt"):
            await agent.regenerate_slide_image(project.id, 1, "make it brighter")

    # Scenario: Missing image_prompt is rejected during image regeneration
    async def test_regenerate_raises_when_no_image_prompt(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir="/tmp/x",
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        slide = _slide(1)
        slide.image_prompt = None
        slide.extras = None
        repo.get_slides_by_project = AsyncMock(return_value=[slide])
        with pytest.raises(ValueError, match="no image_prompt"):
            await agent.regenerate_slide_image(project.id, 1, "change colors")


@pytest.mark.unit
class TestRefineCarouselDesign:
    """The design refinement flow."""

    # Scenario: Apply a CSS override and re-export
    async def test_refinement_writes_css_and_re_exports(self, tmp_path: Path) -> None:
        agent, repo, export, pdf_builder = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[_slide(1), _slide(2)])
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
        export.export_slides.assert_awaited_once()
        pdf_builder.build.assert_called_once()
        assert result.id == project.id

    async def test_refinement_extracts_first_style_block_from_html(
        self, tmp_path: Path
    ) -> None:
        """Given multiple style blocks, when refining, then first CSS block is used."""
        agent, repo, _, _ = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[_slide(1)])
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
        agent, repo, _, _ = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[_slide(1)])
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
        agent, repo, _, _ = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[_slide(1)])
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
        agent, repo, export, _ = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[_slide(1)])
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
        agent, repo, _, _ = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[_slide(1)])
        agent._llm.generate = AsyncMock(return_value="  ")

        with pytest.raises(ValueError, match="empty CSS"):
            await agent.refine_carousel_design(project.id, "make images bigger")

    # Scenario: Missing project is rejected during design refinement
    async def test_refinement_raises_when_project_missing(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
        missing_id = uuid4()
        repo.get_project_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match=str(missing_id)):
            await agent.refine_carousel_design(missing_id, "change layout")

    # Scenario: Missing output_dir is rejected during design refinement
    async def test_refinement_raises_when_no_output_dir(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
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
        agent, repo, _, _ = _agent_with_mocks()
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
