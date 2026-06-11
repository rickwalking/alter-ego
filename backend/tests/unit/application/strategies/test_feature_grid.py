"""Unit tests for FeatureGridStrategy.

Gherkin: tests/features/carousel_slide_layout_strategies.feature
"""

import pytest

from rag_backend.application.services.carousel_template.strategies.feature_grid import (
    FeatureGridStrategy,
)
from rag_backend.domain.protocols.carousel import _RenderOptions

_PALETTE = {"primary": "#3b82f6", "accent": "#f59e0b", "background": "#0a0e17"}


@pytest.mark.unit
class TestFeatureGridStrategy:
    """Scenario: Select feature_grid strategy renders 2-column feature cards."""

    def test_renders_feature_grid(self, sample_project, slide_with_features):
        strategy = FeatureGridStrategy()
        result = strategy.render(
            slide_with_features,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert 'class="feature-grid cols-2"' in result
        assert '<div class="feature-item">' in result
        assert "Fast" in result
        assert "Secure" in result

    def test_renders_heading_and_body(self, sample_project, slide_with_features):
        strategy = FeatureGridStrategy()
        result = strategy.render(
            slide_with_features,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert "Core Features" in result
        assert "What makes us different" in result

    def test_fallback_when_no_features(self, sample_project, slide_empty):
        strategy = FeatureGridStrategy()
        result = strategy.render(
            slide_empty,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert 'class="feature-grid cols-2"' not in result
        assert "No structured data here" in result

    def test_fallback_when_features_empty_list(self, sample_project, slide_with_stats):
        strategy = FeatureGridStrategy()
        slide = dict(slide_with_stats, features=[])
        result = strategy.render(
            slide,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert 'class="feature-grid cols-2"' not in result

    def test_fallback_when_features_none(self, sample_project, slide_with_stats):
        strategy = FeatureGridStrategy()
        slide = dict(slide_with_stats, features=None)
        result = strategy.render(
            slide,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert 'class="feature-grid cols-2"' not in result

    def test_overflow_capped_at_max_items(self, sample_project, slide_with_overflow):
        strategy = FeatureGridStrategy()
        result = strategy.render(
            slide_with_overflow,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert result.count('<div class="feature-item">') <= 4

    def test_non_dict_features_skipped(self, sample_project, slide_with_features):
        strategy = FeatureGridStrategy()
        slide = dict(
            slide_with_features,
            features=[
                {"icon_name": "target", "title": "Good", "body": "Works"},
                "invalid",
            ],
        )
        result = strategy.render(
            slide,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert "Good" in result

    def test_renders_lucide_svg_icons(self, sample_project, slide_with_features):
        strategy = FeatureGridStrategy()
        result = strategy.render(
            slide_with_features,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert result.count('<svg viewBox="0 0 24 24"') == 3
        assert "⚡" not in result
        assert "🔒" not in result

    def test_rejects_legacy_emoji_icon(self, sample_project, slide_with_features):
        strategy = FeatureGridStrategy()
        slide = dict(
            slide_with_features,
            features=[{"icon": "⚡", "title": "Fast", "body": "Legacy emoji"}],
        )
        with pytest.raises(Exception, match="Lucide allowlist"):
            strategy.render(
                slide,
                sample_project,
                _PALETTE,
                options=_RenderOptions(total_slides=7, language="pt"),
            )
