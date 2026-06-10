"""Tests for shared lower-third presentation shell markup."""

import pytest

from rag_backend.application.services.carousel_template.strategies.feature_grid import (
    FeatureGridStrategy,
)
from rag_backend.application.services.carousel_template.strategies.hero_content import (
    HeroContentStrategy,
)


@pytest.mark.unit
class TestLowerThirdShell:
    """Gherkin: Valid lower-third slide markup."""

    def test_hero_content_uses_shared_shell(self, sample_project, sample_theme) -> None:
        result = HeroContentStrategy().render(
            {"number": "3", "type": "content", "heading": "Heading", "body": "Body"},
            sample_project,
            sample_theme,
            7,
            "pt",
        )
        assert 'class="slide-artwork"' in result
        assert 'class="slide-overlay"' in result
        assert 'class="slide-presentation"' in result
        assert 'data-layout="lower-third"' in result
        assert 'class="slide-presentation-copy slide-hero-main"' in result

    def test_feature_grid_uses_shared_shell(self, sample_project, sample_theme) -> None:
        result = FeatureGridStrategy().render(
            {
                "number": "4",
                "type": "content",
                "heading": "Features",
                "body": "Body",
                "features": [
                    {
                        "icon_name": "target",
                        "title": "One",
                        "body": "Detail",
                    }
                ],
            },
            sample_project,
            sample_theme,
            7,
            "pt",
        )
        assert 'class="slide-presentation"' in result
        assert "<svg" in result
