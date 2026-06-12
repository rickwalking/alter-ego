"""Unit tests for carousel refinement mixin.

Feature: Carousel slide image regeneration and design refinement
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel_refinement import (
    _ERR_EMPTY_CSS,
    _ERR_EMPTY_IMAGE_PROMPT,
    _ERR_NO_IMAGE_PROMPT,
    _ERR_NO_OUTPUT_DIR_DESIGN,
    _ERR_NO_OUTPUT_DIR_IMAGE,
    _ERR_NO_SLIDES,
    _ERR_SLIDE_NOT_FOUND,
    CarouselRefinementMixin,
    _render_design_prompt,
    _render_image_rewrite_prompt,
)
from rag_backend.domain.models import CarouselProject, CarouselSlide, CarouselTheme


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class _FakeMixin(CarouselRefinementMixin):
    """Concrete mixin host for unit tests."""

    def __init__(self) -> None:
        self._repo = MagicMock()
        self._repo.get_project_by_id = AsyncMock()
        self._repo.get_slides_by_project = AsyncMock()
        self._repo.update_slide = AsyncMock()
        self._llm = MagicMock()
        self._llm.generate = AsyncMock()
        self._image_registry = MagicMock()
        self._phase4_design = MagicMock()
        self.re_render_slides = AsyncMock()


def _make_project(**overrides: object) -> CarouselProject:
    project = CarouselProject(
        topic="Test",
        audience="Testers",
        niche="Testing",
        theme=CarouselTheme.AUTO,
    )
    for key, value in overrides.items():
        setattr(project, key, value)
    return project


def _make_slide(**overrides: object) -> CarouselSlide:
    slide = CarouselSlide(
        project_id=uuid4(),
        slide_number=1,
        slide_type="intro",
        heading="Heading",
        body="Body",
    )
    for key, value in overrides.items():
        setattr(slide, key, value)
    return slide


# ---------------------------------------------------------------------------
# Prompt rendering (extra coverage to kill mutants)
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRenderImageRewritePromptExtra:
    """Additional edge cases for prompt rendering mutants."""

    def test_fallback_on_any_exception(self) -> None:
        """Given any Exception subclass, when rendering, then fallback is used."""
        with patch(
            "rag_backend.agents.prompts.registry.render_prompt",
            side_effect=Exception("boom"),
        ):
            result = _render_image_rewrite_prompt("x", "y")
        assert result.startswith("You are editing")
        assert "x" in result
        assert "y" in result

    def test_registry_exact_arguments(self) -> None:
        """Given registry call, when rendering, then exact args are passed."""
        with patch(
            "rag_backend.agents.prompts.registry.render_prompt",
            return_value=("ok", {}),
        ) as mock:
            _render_image_rewrite_prompt("instr", "curr")
        args, _ = mock.call_args
        assert args == ("refinement", "image_rewrite")
        kwargs = _.items()
        assert ("version", "v1") in kwargs


@pytest.mark.unit
class TestRenderDesignPromptExtra:
    """Additional edge cases for design prompt rendering mutants."""

    def test_fallback_on_any_exception(self) -> None:
        """Given any Exception subclass, when rendering, then fallback is used."""
        with patch(
            "rag_backend.agents.prompts.registry.render_prompt",
            side_effect=Exception("boom"),
        ):
            result = _render_design_prompt("x", "y")
        assert result.startswith("You are a CSS expert")
        assert "x" in result
        assert "y" in result

    def test_css_passed_as_is(self) -> None:
        """Given CSS, when rendering, then it is passed without truncation."""
        css = "a" * 2000
        with patch(
            "rag_backend.agents.prompts.registry.render_prompt",
            return_value=("ok", {}),
        ) as mock:
            _render_design_prompt("instr", css)
        _, kwargs = mock.call_args
        assert kwargs["variables"]["current_css"] == "a" * 2000


# ---------------------------------------------------------------------------
# regenerate_slide_image
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRegenerateSlideImage:
    """Tests for CarouselRefinementMixin.regenerate_slide_image."""

    @pytest.mark.asyncio
    async def test_project_not_found_raises(self) -> None:
        """Given missing project, when regenerating, then ValueError with exact message."""
        mixin = _FakeMixin()
        mixin._repo.get_project_by_id.return_value = None
        project_id = uuid4()

        with pytest.raises(ValueError, match=str(project_id)):
            await mixin.regenerate_slide_image(project_id, 1, "make it blue")

        mixin._repo.get_project_by_id.assert_awaited_once_with(project_id)

    @pytest.mark.asyncio
    async def test_no_output_dir_raises(self) -> None:
        """Given project without output_dir, when regenerating, then ValueError."""
        mixin = _FakeMixin()
        project = _make_project(output_dir=None)
        mixin._repo.get_project_by_id.return_value = project

        with pytest.raises(
            ValueError, match=_ERR_NO_OUTPUT_DIR_IMAGE.format(project.id)
        ):
            await mixin.regenerate_slide_image(project.id, 1, "x")

    @pytest.mark.asyncio
    async def test_slide_not_found_raises(self) -> None:
        """Given slide absent from project, when regenerating, then ValueError."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = []

        with pytest.raises(
            ValueError, match=_ERR_SLIDE_NOT_FOUND.format(1, project.id)
        ):
            await mixin.regenerate_slide_image(project.id, 1, "x")

    @pytest.mark.asyncio
    async def test_no_image_prompt_raises(self) -> None:
        """Given slide with empty image_prompt, when regenerating, then ValueError."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide(image_prompt=None)
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]

        with pytest.raises(ValueError, match=_ERR_NO_IMAGE_PROMPT.format(1)):
            await mixin.regenerate_slide_image(project.id, 1, "x")

    @pytest.mark.asyncio
    async def test_empty_image_prompt_in_slide_raises(self) -> None:
        """Given slide with empty-string image_prompt, when regenerating, then ValueError."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide(image_prompt="")
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]

        with pytest.raises(ValueError, match=_ERR_NO_IMAGE_PROMPT.format(1)):
            await mixin.regenerate_slide_image(project.id, 1, "x")

    @pytest.mark.asyncio
    async def test_empty_llm_response_raises(self) -> None:
        """Given LLM returns empty string, when regenerating, then ValueError."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide(image_prompt="sunset")
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._llm.generate.return_value = "   "

        with pytest.raises(ValueError, match=_ERR_EMPTY_IMAGE_PROMPT):
            await mixin.regenerate_slide_image(project.id, 1, "x")

        mixin._llm.generate.assert_awaited_once()
        _, kwargs = mixin._llm.generate.call_args
        assert kwargs.get("temperature") == 0.7

    @pytest.mark.asyncio
    async def test_llm_prompt_structure(self) -> None:
        """Given valid inputs, when regenerating, then LLM receives correct prompt."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide(image_prompt="sunset", extras={"image_prompt": "sunset"})
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._llm.generate.return_value = "new prompt"

        with patch(
            "rag_backend.application.services.carousel_refinement.run_image_one",
            return_value="/tmp/out/images/slide_1.jpg",
        ):
            await mixin.regenerate_slide_image(project.id, 1, "make it blue")

        call_args, _ = mixin._llm.generate.call_args
        messages = call_args[0]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert "make it blue" in content
        assert "sunset" in content

    @pytest.mark.asyncio
    async def test_successful_regeneration_updates_slide(self) -> None:
        """Given valid flow, when regenerating, then slide is updated with exact values."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide(
            slide_number=1,
            slide_type="intro",
            image_prompt="old",
            extras={"stats": [{"v": "1"}]},
        )
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._llm.generate.return_value = "  new prompt  "

        with patch(
            "rag_backend.application.services.carousel_refinement.run_image_one",
            return_value="/tmp/out/images/slide_1.jpg",
        ) as mock_run:
            result = await mixin.regenerate_slide_image(
                project.id, 1, "make it futuristic"
            )

        assert result is project
        assert slide.image_prompt == "new prompt"
        assert slide.extras == {"stats": [{"v": "1"}], "image_prompt": "new prompt"}
        mixin._repo.update_slide.assert_awaited_once_with(slide)
        mock_run.assert_awaited_once()
        args, _ = mock_run.call_args
        config = args[0] if args else None
        assert config is not None, "run_image_one should receive ImageGenerationConfig"
        assert config.image_registry is mixin._image_registry
        mixin.re_render_slides.assert_awaited_once_with(project.id)

    @pytest.mark.asyncio
    async def test_successful_regeneration_slide_data_reconstruction(self) -> None:
        """Given valid flow, when regenerating, then run_image_one receives exact SlideData."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide(
            slide_number=3,
            slide_type="content",
            image_prompt="old prompt",
            extras={"features": [{"icon": "✅", "title": "T", "body": "B"}]},
        )
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._llm.generate.return_value = "new prompt"

        captured_slide_data = None

        async def _capture_run_image_one(config, **___):
            nonlocal captured_slide_data
            captured_slide_data = config.slide
            return "/tmp/out/images/slide_3.jpg"

        with patch(
            "rag_backend.application.services.carousel_refinement.run_image_one",
            side_effect=_capture_run_image_one,
        ):
            await mixin.regenerate_slide_image(project.id, 3, "brighter")

        assert captured_slide_data is not None
        assert captured_slide_data.slide_number == 3
        assert captured_slide_data.slide_type == "content"
        assert captured_slide_data.heading == "Heading"
        assert captured_slide_data.body == "Body"
        assert captured_slide_data.image_prompt == "new prompt"
        assert captured_slide_data.features == [
            {"icon": "✅", "title": "T", "body": "B"}
        ]

    @pytest.mark.asyncio
    async def test_successful_regeneration_with_none_extras(self) -> None:
        """Given slide with None extras, when regenerating, then extras dict is created."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide(image_prompt="old", extras=None)
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._llm.generate.return_value = "new"

        with patch(
            "rag_backend.application.services.carousel_refinement.run_image_one",
            return_value="/tmp/out/images/slide_1.jpg",
        ):
            await mixin.regenerate_slide_image(project.id, 1, "x")

        assert slide.extras == {"image_prompt": "new"}


# ---------------------------------------------------------------------------
# refine_carousel_design
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRefineCarouselDesign:
    """Tests for CarouselRefinementMixin.refine_carousel_design."""

    @pytest.mark.asyncio
    async def test_project_not_found_raises(self) -> None:
        """Given missing project, when refining design, then ValueError."""
        mixin = _FakeMixin()
        mixin._repo.get_project_by_id.return_value = None
        project_id = uuid4()

        with pytest.raises(ValueError, match=str(project_id)):
            await mixin.refine_carousel_design(project_id, "dark mode")

    @pytest.mark.asyncio
    async def test_no_output_dir_raises(self) -> None:
        """Given project without output_dir, when refining design, then ValueError."""
        mixin = _FakeMixin()
        project = _make_project(output_dir=None)
        mixin._repo.get_project_by_id.return_value = project

        with pytest.raises(
            ValueError, match=_ERR_NO_OUTPUT_DIR_DESIGN.format(project.id)
        ):
            await mixin.refine_carousel_design(project.id, "dark mode")

    @pytest.mark.asyncio
    async def test_no_slides_raises(self) -> None:
        """Given project with empty slides, when refining design, then ValueError."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = []

        with pytest.raises(ValueError, match=_ERR_NO_SLIDES.format(project.id)):
            await mixin.refine_carousel_design(project.id, "dark mode")

    @pytest.mark.asyncio
    async def test_empty_css_response_raises(self) -> None:
        """Given LLM returns empty CSS, when refining design, then ValueError."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._phase4_design.return_value = "<html><style>body{}</style></html>"
        mixin._llm.generate.return_value = "   "

        with pytest.raises(ValueError, match=_ERR_EMPTY_CSS):
            await mixin.refine_carousel_design(project.id, "dark mode")

        mixin._llm.generate.assert_awaited_once()
        _, kwargs = mixin._llm.generate.call_args
        assert kwargs.get("temperature") == 0.3

    @pytest.mark.asyncio
    async def test_css_extraction_with_style_tags(self) -> None:
        """Given HTML with <style>, when refining, then extracted CSS is passed to LLM."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._phase4_design.return_value = (
            "<html><style>\n.hero { color: red; }\n</style></html>"
        )
        mixin._llm.generate.return_value = ".new { color: blue; }"

        with patch("pathlib.Path.write_text") as mock_write:
            await mixin.refine_carousel_design(project.id, "change color")

        call_args, _ = mixin._llm.generate.call_args
        content = call_args[0][0]["content"]
        assert ".hero { color: red; }" in content
        mock_write.assert_called_once_with(".new { color: blue; }", encoding="utf-8")

    @pytest.mark.asyncio
    async def test_css_extraction_without_style_tags(self) -> None:
        """Given HTML without <style>, when refining, then empty CSS is passed to LLM."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._phase4_design.return_value = "<html><body>no css</body></html>"
        mixin._llm.generate.return_value = "body { margin: 0; }"

        with patch("pathlib.Path.write_text") as mock_write:
            await mixin.refine_carousel_design(project.id, "reset margin")

        call_args, _ = mixin._llm.generate.call_args
        content = call_args[0][0]["content"]
        assert "Existing CSS classes (relevant excerpts):" in content
        assert "```css" in content
        assert "```\n\nReturn ONLY" in content
        mock_write.assert_called_once_with("body { margin: 0; }", encoding="utf-8")

    @pytest.mark.asyncio
    async def test_css_extraction_only_start_tag_missing(self) -> None:
        """Given HTML with only </style>, when refining, then empty CSS is passed."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._phase4_design.return_value = "<html></style></html>"
        mixin._llm.generate.return_value = "body {}"

        with patch("pathlib.Path.write_text") as mock_write:
            await mixin.refine_carousel_design(project.id, "x")

        call_args, _ = mixin._llm.generate.call_args
        content = call_args[0][0]["content"]
        # When start tag is missing, current_css should be ""
        assert "```css\n\n```\n\nReturn ONLY" in content
        mock_write.assert_called_once_with("body {}", encoding="utf-8")

    @pytest.mark.asyncio
    async def test_css_extraction_only_end_tag_missing(self) -> None:
        """Given HTML with only <style>, when refining, then empty CSS is passed."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._phase4_design.return_value = "<html><style>body{}</html>"
        mixin._llm.generate.return_value = "body {}"

        with patch("pathlib.Path.write_text") as mock_write:
            await mixin.refine_carousel_design(project.id, "x")

        call_args, _ = mixin._llm.generate.call_args
        content = call_args[0][0]["content"]
        assert "```css\n\n```\n\nReturn ONLY" in content
        mock_write.assert_called_once_with("body {}", encoding="utf-8")

    @pytest.mark.asyncio
    async def test_markdown_css_fence_stripped(self) -> None:
        """Given LLM wraps CSS in ```css ... ```, when refining, then fences are stripped."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._phase4_design.return_value = "<html><style>a{}</style></html>"
        mixin._llm.generate.return_value = "```css\n.new { color: blue; }\n```"

        with patch("pathlib.Path.write_text") as mock_write:
            await mixin.refine_carousel_design(project.id, "x")

        mock_write.assert_called_once_with(".new { color: blue; }", encoding="utf-8")

    @pytest.mark.asyncio
    async def test_markdown_css_fence_stripped_backticks_only(self) -> None:
        """Given LLM wraps CSS in ``` ... ``` without css label, then fences stripped."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._phase4_design.return_value = "<html><style>a{}</style></html>"
        mixin._llm.generate.return_value = "```\n.new { color: blue; }\n```"

        with patch("pathlib.Path.write_text") as mock_write:
            await mixin.refine_carousel_design(project.id, "x")

        mock_write.assert_called_once_with(".new { color: blue; }", encoding="utf-8")

    @pytest.mark.asyncio
    async def test_markdown_css_fence_stripped_no_end_fence(self) -> None:
        """Given LLM opens with ```css but no closing fence, then start fence stripped."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._phase4_design.return_value = "<html><style>a{}</style></html>"
        mixin._llm.generate.return_value = "```css\n.new { color: blue; }"

        with patch("pathlib.Path.write_text") as mock_write:
            await mixin.refine_carousel_design(project.id, "x")

        mock_write.assert_called_once_with(".new { color: blue; }", encoding="utf-8")

    @pytest.mark.asyncio
    async def test_markdown_css_fence_stripped_no_start_fence(self) -> None:
        """Given LLM closes with ``` but no opening fence, then end fence stripped."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._phase4_design.return_value = "<html><style>a{}</style></html>"
        mixin._llm.generate.return_value = ".new { color: blue; }\n```"

        with patch("pathlib.Path.write_text") as mock_write:
            await mixin.refine_carousel_design(project.id, "x")

        mock_write.assert_called_once_with(".new { color: blue; }", encoding="utf-8")

    @pytest.mark.asyncio
    async def test_write_overrides_failure_raises(self) -> None:
        """Given write fails, when refining design, then ValueError with exact message."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._phase4_design.return_value = "<html><style>a{}</style></html>"
        mixin._llm.generate.return_value = "body {}"

        with (
            patch("pathlib.Path.write_text", side_effect=OSError("disk full")),
            pytest.raises(ValueError, match="disk full"),
        ):
            await mixin.refine_carousel_design(project.id, "x")

    @pytest.mark.asyncio
    async def test_successful_design_refinement(self) -> None:
        """Given valid flow, when refining design, then overrides written and slides re-rendered."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._phase4_design.return_value = "<html><style>.old{}</style></html>"
        mixin._llm.generate.return_value = ".new { color: blue; }"

        with patch("pathlib.Path.write_text") as mock_write:
            result = await mixin.refine_carousel_design(project.id, "make it blue")

        assert result is project
        expected_path = Path("/tmp/out") / "design_overrides.css"
        mock_write.assert_called_once_with(".new { color: blue; }", encoding="utf-8")
        mixin.re_render_slides.assert_awaited_once_with(project.id)

    @pytest.mark.asyncio
    async def test_llm_receives_truncated_css(self) -> None:
        """Given long CSS, when refining design, then LLM prompt truncates CSS to 2000 chars."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        long_css = "a" * 5000
        mixin._phase4_design.return_value = f"<html><style>{long_css}</style></html>"
        mixin._llm.generate.return_value = "body {}"

        with patch("pathlib.Path.write_text"):
            await mixin.refine_carousel_design(project.id, "x")

        call_args, _ = mixin._llm.generate.call_args
        content = call_args[0][0]["content"]
        # The current_css in the prompt should be truncated
        assert long_css not in content
        assert "a" * 2000 in content

    @pytest.mark.asyncio
    async def test_override_css_stripped_twice(self) -> None:
        """Given LLM returns ```css ... ``` with extra whitespace, then stripped correctly."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._phase4_design.return_value = "<html><style>a{}</style></html>"
        mixin._llm.generate.return_value = "  ```css\n.new { color: blue; }\n```  "

        with patch("pathlib.Path.write_text") as mock_write:
            await mixin.refine_carousel_design(project.id, "x")

        mock_write.assert_called_once_with(".new { color: blue; }", encoding="utf-8")

    @pytest.mark.asyncio
    async def test_design_prompt_structure(self) -> None:
        """Given valid inputs, when refining design, then LLM receives correct prompt."""
        mixin = _FakeMixin()
        project = _make_project(output_dir="/tmp/out")
        slide = _make_slide()
        mixin._repo.get_project_by_id.return_value = project
        mixin._repo.get_slides_by_project.return_value = [slide]
        mixin._phase4_design.return_value = (
            "<html><style>.hero{color:red}</style></html>"
        )
        mixin._llm.generate.return_value = "body {}"

        with patch("pathlib.Path.write_text"):
            await mixin.refine_carousel_design(project.id, "make it dark")

        call_args, _ = mixin._llm.generate.call_args
        messages = call_args[0]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert "make it dark" in content
        assert ".hero{color:red}" in content
        assert "Do NOT use <style> tags" in content
        assert "Return ONLY the raw CSS override snippet, nothing else." in content
