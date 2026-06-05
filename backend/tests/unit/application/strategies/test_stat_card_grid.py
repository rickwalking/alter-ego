"""Unit tests for StatCardGridStrategy.

Gherkin: tests/features/carousel_slide_layout_strategies.feature
"""

import pytest

from rag_backend.application.services.carousel_template.strategies.stat_card_grid import (
    StatCardGridStrategy,
)

_PALETTE = {"primary": "#3b82f6", "accent": "#f59e0b", "background": "#0a0e17"}


@pytest.mark.unit
class TestStatCardGridStrategy:
    """Scenario: Select stat_card_grid strategy renders 3-column stat cards."""

    def test_renders_stat_row(self, sample_project, slide_with_stats):
        strategy = StatCardGridStrategy()
        result = strategy.render(slide_with_stats, sample_project, _PALETTE, 7, "pt")
        assert '<div class="stat-row">' in result
        assert '<div class="stat-card">' in result
        assert "10K+" in result
        assert "Users" in result

    def test_renders_heading_and_body(self, sample_project, slide_with_stats):
        strategy = StatCardGridStrategy()
        result = strategy.render(slide_with_stats, sample_project, _PALETTE, 7, "pt")
        assert "Key Metrics" in result
        assert "Our growth in numbers" in result

    def test_includes_slide_number(self, sample_project, slide_with_stats):
        strategy = StatCardGridStrategy()
        result = strategy.render(slide_with_stats, sample_project, _PALETTE, 7, "pt")
        assert "03" in result or "0{number}" not in result

    def test_fallback_when_no_stats(self, sample_project, slide_empty):
        strategy = StatCardGridStrategy()
        result = strategy.render(slide_empty, sample_project, _PALETTE, 7, "pt")
        assert '<div class="stat-row">' not in result
        assert "No structured data here" in result

    def test_fallback_when_stats_empty_list(self, sample_project, slide_with_features):
        strategy = StatCardGridStrategy()
        slide = dict(slide_with_features, stats=[])
        result = strategy.render(slide, sample_project, _PALETTE, 7, "pt")
        assert '<div class="stat-row">' not in result

    def test_fallback_when_stats_none(self, sample_project, slide_with_features):
        strategy = StatCardGridStrategy()
        slide = dict(slide_with_features, stats=None)
        result = strategy.render(slide, sample_project, _PALETTE, 7, "pt")
        assert '<div class="stat-row">' not in result

    def test_overflow_capped_at_max_items(self, sample_project, slide_with_overflow):
        strategy = StatCardGridStrategy()
        result = strategy.render(slide_with_overflow, sample_project, _PALETTE, 7, "pt")
        assert '<div class="stat-row">' in result
        assert result.count('<div class="stat-card">') <= 4

    def test_non_dict_stats_skipped(self, sample_project, slide_with_stats):
        strategy = StatCardGridStrategy()
        slide = dict(slide_with_stats, stats=[{"value": "A", "label": "B"}, "invalid"])
        result = strategy.render(slide, sample_project, _PALETTE, 7, "pt")
        assert '<div class="stat-card">' in result
        assert "A" in result

    def test_render_without_detail(self, sample_project):
        strategy = StatCardGridStrategy()
        slide = {
            "number": "3",
            "type": "content",
            "heading": "Stats",
            "body": "",
            "stats": [{"value": "42", "label": "Answer", "detail": ""}],
            "features": [],
            "insight": None,
            "summary_points": [],
            "tldr_strip": None,
        }
        result = strategy.render(slide, sample_project, _PALETTE, 7, "pt")
        assert "stat-detail" not in result
