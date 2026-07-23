"""Unit tests for the carousel image prompt package renderer.

Gherkin: tests/features/image_generation_provider.feature

Regression guard for AE-0264: the prompt renderer and ``image_provider_registry``
once kept two separate strategy maps that drifted — a combo missing from the
renderer's map silently fell back to the dark default, rendering a light palette
with "neon glow" directives in the 2026-06-22 validation run. AE-0266 Phase 2
folds both into one ``IMAGE_STRATEGY_REGISTRY``; this still guards that every
supported combo resolves to a strategy.
"""

import pytest

from rag_backend.application.services.carousel.image_prompt_package import (
    IMAGE_SAFETY_CLAUSE,
    ImagePromptPackageRequest,
    _strategy_for_project,
    render_image_prompt_package,
)
from rag_backend.application.services.carousel.types import SlideData
from rag_backend.application.services.image_style_strategies import (
    IMAGE_STRATEGY_REGISTRY,
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
        missing = [
            c for c in SUPPORTED_IMAGE_COMBOS if c not in IMAGE_STRATEGY_REGISTRY
        ]
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

    def test_details_land_after_the_locked_directives(self) -> None:
        # AE-0298 structural guard: the user text rides in the Scene trailer
        # AFTER the brand-lock directives. This proves positioning ONLY - it
        # does NOT claim injection-immunity (a trailer directive can still
        # attempt to override the no-text lock; documented residual risk).
        pkg = render_image_prompt_package(
            ImagePromptPackageRequest(
                project=_project_with_details("misty cyber harbor"),
                slide=_slide(),
            )
        )
        rendered = pkg.rendered_prompt
        lock_pos = rendered.index("STRICT:")
        scene_pos = rendered.index("Scene:")
        direction_pos = rendered.index("Visual direction:")
        assert lock_pos < scene_pos < direction_pos

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


def _combo_project(model: str, style: str) -> CarouselProject:
    return CarouselProject(
        topic="Agents",
        audience="Engineers",
        niche="AI",
        theme=CarouselTheme.AI_COMPETITION,
        image_model=model,
        image_style=style,
    )


@pytest.mark.unit
class TestImageSafetyClause:
    """AE-0328 (tests/features/image_generation_provider.feature).

    Prod incident 2026-07-22: a published slide contained nudity — the
    project's custom_visual_details steered an unconstrained "AI entity"
    scene into humanoid output. The clause must ride EVERY prompt.
    """

    # Scenario: Every rendered slide prompt carries the safety clause
    @pytest.mark.parametrize(("model", "style"), sorted(SUPPORTED_IMAGE_COMBOS))
    def test_clause_present_for_every_supported_combo(
        self, model: str, style: str
    ) -> None:
        pkg = render_image_prompt_package(
            ImagePromptPackageRequest(
                project=_combo_project(model, style),
                slide=_slide(),
                theme=CAROUSEL_THEMES["ai_competition"],
            )
        )
        assert IMAGE_SAFETY_CLAUSE in pkg.rendered_prompt
        assert IMAGE_SAFETY_CLAUSE in pkg.raw_prompt

    def test_clause_present_without_custom_details(self) -> None:
        pkg = render_image_prompt_package(
            ImagePromptPackageRequest(
                project=_project_with_details(None), slide=_slide()
            )
        )
        assert IMAGE_SAFETY_CLAUSE in pkg.rendered_prompt

    # Scenario: Steering custom visual details cannot escape the safety clause
    def test_clause_survives_steering_details_and_lands_after_them(self) -> None:
        pkg = render_image_prompt_package(
            ImagePromptPackageRequest(
                project=_project_with_details(
                    "Ghost in the Shell style female hologram, sensual"
                ),
                slide=_slide(),
            )
        )
        rendered = pkg.rendered_prompt
        assert IMAGE_SAFETY_CLAUSE in rendered
        # The guard is the LAST word the model reads — after the user text.
        assert rendered.index("Visual direction:") < rendered.index(
            "SAFETY (non-negotiable"
        )

    # Scenario: Revision feedback rebuilds still carry the safety clause
    def test_clause_survives_revision_feedback_append(self) -> None:
        # Revision feedback is appended to custom_visual_details (AE-0261);
        # the rebuilt prompt flows through the same funnel.
        pkg = render_image_prompt_package(
            ImagePromptPackageRequest(
                project=_project_with_details(
                    "misty cyber harbor. Revision feedback: make the entity glow"
                ),
                slide=_slide(),
            )
        )
        assert IMAGE_SAFETY_CLAUSE in pkg.rendered_prompt

    def test_clause_present_on_empty_scene(self) -> None:
        pkg = render_image_prompt_package(
            ImagePromptPackageRequest(
                project=_project_with_details(None),
                slide=SlideData(
                    slide_number=2,
                    slide_type="content",
                    heading="h",
                    body="b",
                    image_prompt="",
                ),
            )
        )
        assert IMAGE_SAFETY_CLAUSE in pkg.rendered_prompt


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
