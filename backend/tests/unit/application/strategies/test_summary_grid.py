"""Unit tests for SummaryGridStrategy."""

import pytest

from rag_backend.application.services.carousel_template.strategies.summary_grid import (
    SummaryGridStrategy,
)
from rag_backend.domain.protocols.carousel import _RenderOptions

_PALETTE = {"primary": "#3b82f6", "accent": "#f59e0b", "background": "#0a0e17"}


@pytest.mark.unit
class TestSummaryGridStrategy:
    def test_renders_summary_grid(self, sample_project):
        strategy = SummaryGridStrategy()
        slide = {
            "number": "2",
            "type": "summary",
            "heading": "What you will learn",
            "body": "",
            "summary_points": [
                {
                    "icon_name": "book-open",
                    "title": "Origin",
                    "body": "Where the term comes from",
                },
                {
                    "icon_name": "brain",
                    "title": "Components",
                    "body": "What makes up a harness",
                },
                {
                    "icon_name": "target",
                    "title": "Why it matters",
                    "body": "Why teams should care",
                },
            ],
        }
        result = strategy.render(
            slide,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert 'class="summary-grid"' in result
        assert "Origin" in result
        assert "Why it matters" in result

    def test_fallback_without_summary_points(self, sample_project, slide_empty):
        strategy = SummaryGridStrategy()
        result = strategy.render(
            slide_empty,
            sample_project,
            _PALETTE,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert 'class="summary-grid"' not in result
