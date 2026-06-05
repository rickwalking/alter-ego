"""Unit tests for SlideLayoutRegistry.

Gherkin: tests/features/carousel_slide_layout_strategies.feature
"""

import pytest

from rag_backend.application.services.carousel_template.strategies.hero_content import (
    HeroContentStrategy,
)
from rag_backend.application.services.carousel_template.strategies.intro import (
    IntroHeroStrategy,
)
from rag_backend.application.services.carousel_template.strategies.registry import (
    SlideLayoutRegistry,
)
from rag_backend.domain.protocols import StrategyNotFoundError


@pytest.mark.unit
class TestSlideLayoutRegistry:
    """Scenario: Registry manages strategy registration and lookup."""

    def test_register_and_get(self):
        registry = SlideLayoutRegistry()
        strategy = HeroContentStrategy()
        registry.register(strategy)
        assert registry.get("hero_content") is strategy

    def test_register_duplicate_raises(self):
        registry = SlideLayoutRegistry()
        registry.register(HeroContentStrategy())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(HeroContentStrategy())

    def test_get_not_found_raises(self):
        registry = SlideLayoutRegistry()
        with pytest.raises(StrategyNotFoundError):
            registry.get("nonexistent")

    def test_list_returns_all(self):
        registry = SlideLayoutRegistry()
        registry.register(HeroContentStrategy())
        registry.register(IntroHeroStrategy())
        result = registry.list()
        assert len(result) == 2
        names = {r["name"] for r in result}
        assert "hero_content" in names
        assert "intro_hero" in names

    def test_list_includes_display_name(self):
        registry = SlideLayoutRegistry()
        registry.register(HeroContentStrategy())
        result = registry.list()
        assert result[0]["display_name"] == "Hero Content"

    def test_find_for_slide_matches_preferred(self, registry):
        strategy = registry.find_for_slide("content", preferred="stat_card_grid")
        assert strategy.strategy_name == "stat_card_grid"

    def test_find_for_slide_falls_back_when_preferred_unsupported(self, registry):
        strategy = registry.find_for_slide("content", preferred="intro_hero")
        assert strategy.strategy_name != "intro_hero"

    def test_find_for_slide_falls_back_to_hero_content(self, registry):
        strategy = registry.find_for_slide("unknown_slide_type")
        assert strategy.strategy_name == "hero_content"

    def test_find_for_slide_preferred_unsupported_type_uses_any(self, registry):
        strategy = registry.find_for_slide("summary", preferred="feature_grid")
        assert strategy.strategy_name != "feature_grid"

    def test_find_for_slide_intro_only_matches_intro(self, registry):
        strategy = registry.find_for_slide("intro")
        assert strategy.strategy_name == "intro_hero"

    def test_find_for_slide_cta_only_matches_cta(self, registry):
        strategy = registry.find_for_slide("cta")
        assert strategy.strategy_name == "cta_centered"

    def test_bootstrap_registers_all_seven(self, registry):
        result = registry.list()
        assert len(result) == 7

    def test_bootstrap_has_all_strategy_names(self, registry):
        names = {r["name"] for r in registry.list()}
        expected = {
            "intro_hero",
            "hero_content",
            "cta_centered",
            "stat_card_grid",
            "feature_grid",
            "insight_quote",
            "numbered_list",
        }
        assert names == expected
