"""Unit tests for NumberedListStrategy.

Gherkin: tests/features/carousel_slide_layout_strategies.feature
"""

import pytest

from rag_backend.application.services.carousel_template.strategies.numbered_list import (
    NumberedListStrategy,
)
from rag_backend.domain.protocols.carousel import _RenderOptions

_PALETTE = {"primary": "#3b82f6", "accent": "#f59e0b", "background": "#0a0e17"}


@pytest.mark.unit
class TestNumberedListStrategy:
    """Scenario: Select numbered_list strategy renders step list."""

    def test_renders_numbered_steps(self, sample_project, slide_with_features):
        strategy = NumberedListStrategy()
        result = strategy.render(
            slide_with_features,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert '<div class="feature-item">' in result
        assert "1." in result
        assert "Fast" in result
        assert "2." in result
        assert "Secure" in result

    def test_renders_heading_and_body(self, sample_project, slide_with_features):
        strategy = NumberedListStrategy()
        result = strategy.render(
            slide_with_features,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert "Core Features" in result
        assert "What makes us different" in result

    def test_fallback_when_no_features(self, sample_project, slide_empty):
        strategy = NumberedListStrategy()
        result = strategy.render(
            slide_empty,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert "1." not in result
        assert "No structured data here" in result

    def test_fallback_when_features_empty_list(self, sample_project, slide_with_stats):
        strategy = NumberedListStrategy()
        slide = dict(slide_with_stats, features=[])
        result = strategy.render(
            slide,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert "1." not in result

    def test_fallback_when_features_none(self, sample_project, slide_with_stats):
        strategy = NumberedListStrategy()
        slide = dict(slide_with_stats, features=None)
        result = strategy.render(
            slide,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert "1." not in result

    def test_overflow_capped_at_max_items(self, sample_project, slide_with_overflow):
        strategy = NumberedListStrategy()
        result = strategy.render(
            slide_with_overflow,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        step_count = result.count('<div class="feature-item">')
        assert step_count <= 4

    def test_non_dict_features_skipped(self, sample_project, slide_with_features):
        strategy = NumberedListStrategy()
        slide = dict(
            slide_with_features,
            features=[{"icon": "📌", "title": "First", "body": "Step one"}, "invalid"],
        )
        result = strategy.render(
            slide,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert "First" in result

    def test_mono_font_class_present(self, sample_project, slide_with_features):
        strategy = NumberedListStrategy()
        result = strategy.render(
            slide_with_features,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert "numbered-step" in result
