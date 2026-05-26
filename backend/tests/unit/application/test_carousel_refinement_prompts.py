"""Unit tests for carousel refinement prompt rendering.

Feature: Carousel image and design refinement prompts
"""

from unittest.mock import patch

import pytest

from rag_backend.application.services.carousel_refinement import (
    DESIGN_PROMPT_TEMPLATE,
    IMAGE_PROMPT_REWRITE_TEMPLATE,
    _render_design_prompt,
    _render_image_rewrite_prompt,
)


@pytest.mark.unit
class TestRenderImageRewritePrompt:
    """Direct tests for image prompt rewrite rendering."""

    def test_fallback_includes_instruction_and_current_prompt(self) -> None:
        """Given registry failure, when rendering, then inline template is used."""
        with patch(
            "rag_backend.agents.prompts.registry.render_prompt",
            side_effect=ImportError("registry unavailable"),
        ):
            result = _render_image_rewrite_prompt(
                "make it futuristic", "sunset over the ocean"
            )

        assert result == IMAGE_PROMPT_REWRITE_TEMPLATE.format(
            instruction="make it futuristic",
            current_prompt="sunset over the ocean",
        )
        assert "Instruction: make it futuristic" in result
        assert "sunset over the ocean" in result

    def test_uses_registry_when_available(self) -> None:
        """Given registry success, when rendering, then registry prompt is returned."""
        with patch(
            "rag_backend.agents.prompts.registry.render_prompt",
            return_value=("registry image prompt", {}),
        ) as mock_render:
            result = _render_image_rewrite_prompt("change colors", "a forest scene")

        mock_render.assert_called_once_with(
            "refinement",
            "image_rewrite",
            variables={
                "instruction": "change colors",
                "current_prompt": "a forest scene",
            },
            version="v1",
        )
        assert result == "registry image prompt"


@pytest.mark.unit
class TestRenderDesignPrompt:
    """Direct tests for design CSS prompt rendering."""

    def test_fallback_includes_instruction_and_css(self) -> None:
        """Given registry failure, when rendering, then inline template is used."""
        with patch(
            "rag_backend.agents.prompts.registry.render_prompt",
            side_effect=RuntimeError("registry unavailable"),
        ):
            result = _render_design_prompt(
                "make images bigger", ".hero-img { height: 400px; }"
            )

        assert result == DESIGN_PROMPT_TEMPLATE.format(
            instruction="make images bigger",
            current_css=".hero-img { height: 400px; }",
        )
        assert "make images bigger" in result
        assert ".hero-img { height: 400px; }" in result

    def test_uses_registry_when_available(self) -> None:
        """Given registry success, when rendering, then registry prompt is returned."""
        with patch(
            "rag_backend.agents.prompts.registry.render_prompt",
            return_value=("registry design prompt", {}),
        ) as mock_render:
            result = _render_design_prompt("dark mode", "body { color: black; }")

        mock_render.assert_called_once_with(
            "refinement",
            "design_css",
            variables={
                "instruction": "dark mode",
                "current_css": "body { color: black; }",
            },
            version="v1",
        )
        assert result == "registry design prompt"
