"""Unit tests for image style strategies.

Gherkin: tests/features/image_generation_provider.feature
"""

import pytest

from rag_backend.application.services.image_style_strategies import (
    GeminiComicNeonStrategy,
    OpenAICinematicStrategy,
    OpenAIFlatEditorialStrategy,
    OpenAIHyperrealStrategy,
    OpenAINeoAnimeStrategy,
)

_PALETTE = {
    "primary": "#3b82f6",
    "accent": "#f59e0b",
    "background": "#0a0e17",
}

_LIGHT_PALETTE = {
    "primary": "#111827",
    "accent": "#2563eb",
    "background": "#f7f5f0",
}


@pytest.mark.unit
class TestGeminiComicNeonStrategy:
    """Scenario: Default provider + style when caller omits both fields."""

    def test_includes_comic_manga_marker(self) -> None:
        result = GeminiComicNeonStrategy().wrap("scene", _PALETTE)
        assert "Comic/manga style illustration" in result

    def test_injects_palette_colors(self) -> None:
        result = GeminiComicNeonStrategy().wrap("scene", _PALETTE)
        assert "#3b82f6" in result
        assert "#f59e0b" in result
        assert "#0a0e17" in result

    def test_scene_appears_after_directives(self) -> None:
        # Scenario: Style wrapper never rewrites the LLM scene description.
        scene = "a hooded figure at a neon terminal"
        result = GeminiComicNeonStrategy().wrap(scene, _PALETTE)
        assert scene in result
        assert result.index(scene) > result.index("Comic/manga")


@pytest.mark.unit
class TestOpenAIHyperrealStrategy:
    """Scenario: Caller picks OpenAI hyperreal preset."""

    def test_includes_hyperreal_marker(self) -> None:
        result = OpenAIHyperrealStrategy().wrap("scene", _PALETTE)
        assert "Hyperreal illustration" in result

    def test_forbids_readable_text(self) -> None:
        result = OpenAIHyperrealStrategy().wrap("scene", _PALETTE)
        lowered = result.lower()
        assert "no readable text" in lowered
        assert "no logos" in lowered
        assert "no captions" in lowered
        assert "no ui labels" in lowered

    def test_scene_preserved_verbatim(self) -> None:
        scene = "engineer staring at three holographic orbs"
        result = OpenAIHyperrealStrategy().wrap(scene, _PALETTE)
        assert scene in result


@pytest.mark.unit
class TestOpenAICinematicStrategy:
    """Scenario: Caller picks OpenAI cinematic preset."""

    def test_includes_cinematic_marker(self) -> None:
        result = OpenAICinematicStrategy().wrap("scene", _PALETTE)
        assert "Cinematic photoreal still frame" in result

    def test_scene_preserved_verbatim(self) -> None:
        scene = "rain-soaked neon alley, mid-shot"
        result = OpenAICinematicStrategy().wrap(scene, _PALETTE)
        assert scene in result


@pytest.mark.unit
class TestOpenAINeoAnimeStrategy:
    """Scenario: Caller picks OpenAI neo-anime preset."""

    def test_includes_neo_anime_marker(self) -> None:
        result = OpenAINeoAnimeStrategy().wrap("scene", _PALETTE)
        assert "Cel-animated feature film still" in result

    def test_scene_preserved_verbatim(self) -> None:
        scene = "cyborg on a monorail platform at dusk"
        result = OpenAINeoAnimeStrategy().wrap(scene, _PALETTE)
        assert scene in result


@pytest.mark.unit
class TestOpenAIFlatEditorialStrategy:
    """Scenario: Caller picks OpenAI flat-editorial preset (light palette)."""

    def test_includes_flat_editorial_marker(self) -> None:
        result = OpenAIFlatEditorialStrategy().wrap("scene", _LIGHT_PALETTE)
        assert "Flat editorial vector illustration" in result

    def test_uses_light_background_phrasing_not_neon(self) -> None:
        # The light strategy must not contradict a light palette with the
        # dark "neon glow" phrasing reserved for the dark strategies.
        result = OpenAIFlatEditorialStrategy().wrap("scene", _LIGHT_PALETTE)
        assert "Light background" in result
        assert "neon glow" not in result.lower()

    def test_injects_light_palette_colors(self) -> None:
        result = OpenAIFlatEditorialStrategy().wrap("scene", _LIGHT_PALETTE)
        assert "#111827" in result
        assert "#2563eb" in result
        assert "#f7f5f0" in result

    def test_forbids_readable_text(self) -> None:
        result = OpenAIFlatEditorialStrategy().wrap("scene", _LIGHT_PALETTE)
        assert "no readable text" in result.lower()

    def test_scene_preserved_verbatim(self) -> None:
        scene = "a single desk lamp over an open notebook"
        result = OpenAIFlatEditorialStrategy().wrap(scene, _LIGHT_PALETTE)
        assert scene in result


@pytest.mark.unit
class TestSceneInvariant:
    """Scenario: Style wrapper never rewrites the LLM scene description.

    The same scene should appear verbatim and always *after* the style
    directives for every registered strategy.
    """

    @pytest.mark.parametrize(
        "strategy",
        [
            GeminiComicNeonStrategy(),
            OpenAICinematicStrategy(),
            OpenAIHyperrealStrategy(),
            OpenAINeoAnimeStrategy(),
            OpenAIFlatEditorialStrategy(),
        ],
    )
    def test_scene_verbatim_and_trailing(self, strategy) -> None:
        scene = "a hooded figure at a neon terminal"
        result = strategy.wrap(scene, _PALETTE)
        assert scene in result
        # Scene text is the last meaningful content in the prompt.
        assert result.rstrip().endswith(scene)

    def test_handles_missing_palette_keys_gracefully(self) -> None:
        # Defensive: partial theme should not blow up.
        result = GeminiComicNeonStrategy().wrap("scene", {})
        assert "scene" in result
