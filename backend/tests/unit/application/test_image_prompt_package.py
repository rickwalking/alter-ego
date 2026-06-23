"""Unit tests for the carousel image prompt package renderer.

Gherkin: tests/features/image_generation_provider.feature

Regression guard for AE-0264: the prompt renderer keeps its own
``_STRATEGY_MAP`` separate from ``image_provider_registry``. A combo missing
here silently falls back to the dark default strategy, which rendered a light
palette with "neon glow" directives in the 2026-06-22 validation run.
"""

import pytest

from rag_backend.application.services.carousel.image_prompt_package import (
    _STRATEGY_MAP,
    ImagePromptPackageRequest,
    _strategy_for_project,
    render_image_prompt_package,
)
from rag_backend.application.services.carousel.types import SlideData
from rag_backend.application.services.image_style_strategies import (
    OpenAIFlatEditorialStrategy,
)
from rag_backend.domain.constants import (
    CAROUSEL_THEMES,
    IMAGE_MODEL_OPENAI,
    IMAGE_STYLE_FLAT_EDITORIAL,
    SUPPORTED_IMAGE_COMBOS,
)
from rag_backend.domain.models import CarouselProject, CarouselTheme


def _light_project() -> CarouselProject:
    return CarouselProject(
        topic="Spec-driven development",
        audience="Engineers",
        niche="Software",
        theme=CarouselTheme.PAPER_EDITORIAL,
        image_model=IMAGE_MODEL_OPENAI,
        image_style=IMAGE_STYLE_FLAT_EDITORIAL,
    )


def _slide() -> SlideData:
    return SlideData(
        slide_number=1,
        slide_type="content",
        heading="Write the spec first",
        body="...",
        image_prompt="a tidy desk with an open notebook",
    )


@pytest.mark.unit
class TestStrategyResolution:
    def test_flat_editorial_resolves_to_editorial_strategy(self) -> None:
        strategy = _strategy_for_project(_light_project())
        assert isinstance(strategy, OpenAIFlatEditorialStrategy)

    def test_every_supported_combo_has_a_strategy(self) -> None:
        # Guard against the registry / prompt-map drift that made a light
        # palette fall back to the dark default (AE-0264).
        missing = [c for c in SUPPORTED_IMAGE_COMBOS if c not in _STRATEGY_MAP]
        assert missing == [], f"combos with no prompt strategy: {missing}"


def _project_with_details(details: str | None) -> CarouselProject:
    return CarouselProject(
        topic="Agents",
        audience="Engineers",
        niche="AI",
        theme=CarouselTheme.AI_COMPETITION,
        image_model=IMAGE_MODEL_OPENAI,
        image_style="neo_anime",
        custom_visual_details=details,
    )


@pytest.mark.unit
class TestCustomVisualDetails:
    # AE-0263 (inject project visual direction) + AE-0261 (revision changes prompt).
    def test_details_injected_into_scene(self) -> None:
        pkg = render_image_prompt_package(
            ImagePromptPackageRequest(
                project=_project_with_details("Rio de Janeiro skyline at golden hour"),
                slide=_slide(),
            )
        )
        assert "Visual direction: Rio de Janeiro skyline" in pkg.rendered_prompt

    def test_no_details_leaves_scene_unchanged(self) -> None:
        base = render_image_prompt_package(
            ImagePromptPackageRequest(
                project=_project_with_details(None), slide=_slide()
            )
        )
        assert "Visual direction:" not in base.rendered_prompt

    def test_details_change_the_prompt_hash(self) -> None:
        # The reuse cache keys on prompt_hash; new direction must bust it so a
        # revision actually regenerates instead of returning the cached image.
        without = render_image_prompt_package(
            ImagePromptPackageRequest(
                project=_project_with_details(None), slide=_slide()
            )
        )
        with_d = render_image_prompt_package(
            ImagePromptPackageRequest(
                project=_project_with_details("set at night, neon rain"),
                slide=_slide(),
            )
        )
        assert without.prompt_hash != with_d.prompt_hash


@pytest.mark.unit
class TestLightPromptRendering:
    def test_light_project_prompt_is_editorial_not_neon(self) -> None:
        package = render_image_prompt_package(
            ImagePromptPackageRequest(
                project=_light_project(),
                slide=_slide(),
                theme=CAROUSEL_THEMES["paper_editorial"],
            )
        )
        rendered = package.rendered_prompt
        assert "Flat editorial vector illustration" in rendered
        assert "Light background" in rendered
        assert "neon glow" not in rendered.lower()
        # The light palette colors still flow into the prompt.
        assert CAROUSEL_THEMES["paper_editorial"]["background"] in rendered
