"""Contract tests for the consolidated image-strategy registry (AE-0266 Ph2).

Gherkin: tests/features/image_generation_provider.feature

``IMAGE_STRATEGY_REGISTRY`` is the single source of truth for which strategy
class renders each ``(image_model, image_style)`` combo. Before AE-0266 Phase 2
the prompt renderer and the provider registry each hand-maintained their own
parallel map; they drifted and a light palette fell back to the dark "neon
glow" default (AE-0264). These tests pin the SSOT so the drift class cannot
return: the registry keys must equal ``SUPPORTED_IMAGE_COMBOS``, and both
consumers must resolve the exact strategy the registry declares.
"""

from unittest.mock import AsyncMock

import pytest

from rag_backend.application.services.carousel.image_prompt_package import (
    _strategy_for_project,
)
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.application.services.image_style_strategies import (
    IMAGE_STRATEGY_REGISTRY,
)
from rag_backend.domain.constants import SUPPORTED_IMAGE_COMBOS
from rag_backend.domain.models import CarouselProject, CarouselTheme


def _registry() -> ImageProviderRegistry:
    return ImageProviderRegistry(
        gemini_service=AsyncMock(),
        openai_service=AsyncMock(),
    )


def _project(model: str, style: str) -> CarouselProject:
    return CarouselProject(
        topic="Spec-driven development",
        audience="Engineers",
        niche="Software",
        theme=CarouselTheme.AI_COMPETITION,
        image_model=model,
        image_style=style,
    )


@pytest.mark.unit
class TestImageStrategyRegistryIsSingleSourceOfTruth:
    def test_registry_keys_equal_supported_combos(self) -> None:
        # If a combo is added to one but not the other, this fails — the
        # validation set and the strategy map can no longer silently diverge.
        assert set(IMAGE_STRATEGY_REGISTRY) == SUPPORTED_IMAGE_COMBOS

    def test_provider_registry_uses_the_registry_strategy(self) -> None:
        provider_registry = _registry()
        for (model, style), strategy_cls in IMAGE_STRATEGY_REGISTRY.items():
            provider = provider_registry.resolve(model, style)
            assert type(provider.strategy) is strategy_cls

    def test_prompt_renderer_uses_the_registry_strategy(self) -> None:
        for (model, style), strategy_cls in IMAGE_STRATEGY_REGISTRY.items():
            resolved = _strategy_for_project(_project(model, style))
            assert type(resolved) is strategy_cls

    def test_both_consumers_agree_for_every_combo(self) -> None:
        # The structural guarantee AE-0264 lacked: same combo -> same strategy
        # class from both the renderer and the provider registry.
        provider_registry = _registry()
        for model, style in SUPPORTED_IMAGE_COMBOS:
            via_renderer = type(_strategy_for_project(_project(model, style)))
            via_provider = type(provider_registry.resolve(model, style).strategy)
            assert via_renderer is via_provider
