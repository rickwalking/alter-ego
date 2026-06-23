"""Unit tests for ImageProviderRegistry.

Gherkin: tests/features/image_generation_provider.feature
"""

from unittest.mock import AsyncMock

import pytest

from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.application.services.image_style_strategies import (
    GeminiComicNeonStrategy,
    OpenAICinematicStrategy,
    OpenAIFlatEditorialStrategy,
    OpenAIHyperrealStrategy,
    OpenAINeoAnimeStrategy,
)
from rag_backend.domain.constants import (
    IMAGE_MODEL_GEMINI,
    IMAGE_MODEL_OPENAI,
    IMAGE_STYLE_CINEMATIC,
    IMAGE_STYLE_COMIC_NEON,
    IMAGE_STYLE_FLAT_EDITORIAL,
    IMAGE_STYLE_HYPERREAL,
    IMAGE_STYLE_NEO_ANIME,
)


def _registry() -> ImageProviderRegistry:
    gemini = AsyncMock()
    openai = AsyncMock()
    return ImageProviderRegistry(gemini_service=gemini, openai_service=openai)


@pytest.mark.unit
class TestImageProviderRegistry:
    """Scenario: Incompatible combo rejected."""

    def test_default_combo_returns_gemini_comic_neon(self) -> None:
        provider = _registry().resolve(IMAGE_MODEL_GEMINI, IMAGE_STYLE_COMIC_NEON)
        assert isinstance(provider.strategy, GeminiComicNeonStrategy)

    def test_openai_hyperreal_returns_right_strategy(self) -> None:
        provider = _registry().resolve(IMAGE_MODEL_OPENAI, IMAGE_STYLE_HYPERREAL)
        assert isinstance(provider.strategy, OpenAIHyperrealStrategy)

    def test_openai_cinematic_returns_right_strategy(self) -> None:
        provider = _registry().resolve(IMAGE_MODEL_OPENAI, IMAGE_STYLE_CINEMATIC)
        assert isinstance(provider.strategy, OpenAICinematicStrategy)

    def test_openai_neo_anime_returns_right_strategy(self) -> None:
        provider = _registry().resolve(IMAGE_MODEL_OPENAI, IMAGE_STYLE_NEO_ANIME)
        assert isinstance(provider.strategy, OpenAINeoAnimeStrategy)

    def test_openai_flat_editorial_returns_right_strategy(self) -> None:
        provider = _registry().resolve(
            IMAGE_MODEL_OPENAI, IMAGE_STYLE_FLAT_EDITORIAL
        )
        assert isinstance(provider.strategy, OpenAIFlatEditorialStrategy)

    def test_unsupported_combo_raises_value_error(self) -> None:
        # (gemini, cinematic) is deliberately not in SUPPORTED_IMAGE_COMBOS.
        with pytest.raises(ValueError, match="not supported"):
            _registry().resolve(IMAGE_MODEL_GEMINI, IMAGE_STYLE_CINEMATIC)

    def test_unknown_model_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="not supported"):
            _registry().resolve("dalle-3", IMAGE_STYLE_HYPERREAL)

    def test_unknown_style_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="not supported"):
            _registry().resolve(IMAGE_MODEL_OPENAI, "ukiyo_e")
