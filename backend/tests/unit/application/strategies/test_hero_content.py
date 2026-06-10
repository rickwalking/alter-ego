"""Tests for the hero content carousel strategy."""

import pytest

from rag_backend.application.services.carousel_template.strategies.hero_content import (
    HeroContentStrategy,
)


@pytest.mark.unit
class TestHeroContentStrategy:
    """Hero content rendering behavior."""

    def test_renders_global_swipe_label_for_portuguese(
        self,
        sample_project,
        sample_theme,
    ) -> None:
        result = HeroContentStrategy().render(
            {"number": "2", "type": "summary", "heading": "Resumo", "body": "Body"},
            sample_project,
            sample_theme,
            7,
            "pt",
        )

        assert "Swipe \u2192" in result
        assert "Deslize" not in result

    def test_renders_global_swipe_label_for_english(
        self,
        sample_project,
        sample_theme,
    ) -> None:
        result = HeroContentStrategy().render(
            {"number": "2", "type": "summary", "heading": "Summary", "body": "Body"},
            sample_project,
            sample_theme,
            7,
            "en",
        )

        assert "Swipe \u2192" in result
        assert "Deslize" not in result
