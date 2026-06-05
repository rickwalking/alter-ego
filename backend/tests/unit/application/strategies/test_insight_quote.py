"""Unit tests for InsightQuoteStrategy.

Gherkin: tests/features/carousel_slide_layout_strategies.feature
"""

import pytest

from rag_backend.application.services.carousel_template.strategies.insight_quote import (
    InsightQuoteStrategy,
)

_PALETTE = {"primary": "#3b82f6", "accent": "#f59e0b", "background": "#0a0e17"}


@pytest.mark.unit
class TestInsightQuoteStrategy:
    """Scenario: Select insight_quote strategy renders quote card."""

    def test_renders_insight_card(self, sample_project, slide_with_insight):
        strategy = InsightQuoteStrategy()
        result = strategy.render(slide_with_insight, sample_project, _PALETTE, 7, "pt")
        assert '<div class="insight-card">' in result
        assert "AI will transform every industry" in result
        assert "Andrew Ng" in result

    def test_renders_heading(self, sample_project, slide_with_insight):
        strategy = InsightQuoteStrategy()
        result = strategy.render(slide_with_insight, sample_project, _PALETTE, 7, "pt")
        assert "Key Insight" in result

    def test_fallback_when_no_insight(self, sample_project, slide_empty):
        strategy = InsightQuoteStrategy()
        result = strategy.render(slide_empty, sample_project, _PALETTE, 7, "pt")
        assert '<div class="insight-card">' not in result

    def test_fallback_when_insight_is_not_dict(self, sample_project, slide_with_stats):
        strategy = InsightQuoteStrategy()
        slide = dict(slide_with_stats, insight="just a string")
        result = strategy.render(slide, sample_project, _PALETTE, 7, "pt")
        assert '<div class="insight-card">' not in result

    def test_fallback_when_insight_has_empty_quote(self, sample_project):
        strategy = InsightQuoteStrategy()
        slide = {
            "number": "5",
            "type": "closing",
            "heading": "Insight",
            "body": "",
            "stats": [],
            "features": [],
            "insight": {"quote": "", "attribution": "Someone"},
            "summary_points": [],
            "tldr_strip": None,
        }
        result = strategy.render(slide, sample_project, _PALETTE, 7, "pt")
        assert '<div class="insight-card">' not in result

    def test_renders_attribution(self, sample_project, slide_with_insight):
        strategy = InsightQuoteStrategy()
        result = strategy.render(slide_with_insight, sample_project, _PALETTE, 7, "pt")
        assert '<span class="insight-attribution">' in result

    def test_skips_attribution_when_missing(self, sample_project):
        strategy = InsightQuoteStrategy()
        slide = {
            "number": "5",
            "type": "closing",
            "heading": "Insight",
            "body": "",
            "stats": [],
            "features": [],
            "insight": {"quote": "Great quote", "attribution": ""},
            "summary_points": [],
            "tldr_strip": None,
        }
        result = strategy.render(slide, sample_project, _PALETTE, 7, "pt")
        assert "insight-attribution" not in result

    def test_renders_body_when_present(self, sample_project):
        strategy = InsightQuoteStrategy()
        slide = {
            "number": "5",
            "type": "closing",
            "heading": "Insight",
            "body": "Context paragraph",
            "stats": [],
            "features": [],
            "insight": {"quote": "A quote", "attribution": "Author"},
            "summary_points": [],
            "tldr_strip": None,
        }
        result = strategy.render(slide, sample_project, _PALETTE, 7, "pt")
        assert "Context paragraph" in result
