"""Protocol contract tests — all strategies must satisfy the SlideLayoutStrategy Protocol.

Gherkin: tests/features/carousel_slide_layout_strategies.feature
"""

import pytest


@pytest.mark.unit
class TestSlideLayoutStrategyProtocol:
    """Scenario: All strategies satisfy the SlideLayoutStrategy interface."""

    def test_each_strategy_has_strategy_name(self, all_strategies):
        for strategy in all_strategies:
            assert isinstance(strategy.strategy_name, str)
            assert len(strategy.strategy_name) > 0

    def test_each_strategy_has_display_name(self, all_strategies):
        for strategy in all_strategies:
            assert isinstance(strategy.display_name, str)
            assert len(strategy.display_name) > 0

    def test_each_strategy_has_supported_slide_types(self, all_strategies):
        for strategy in all_strategies:
            assert isinstance(strategy.supported_slide_types, frozenset)
            assert len(strategy.supported_slide_types) > 0

    def test_each_strategy_has_render_method(self, all_strategies):
        for strategy in all_strategies:
            assert hasattr(strategy, "render")
            assert callable(strategy.render)

    def test_render_returns_string(
        self,
        all_strategies,
        slide_with_stats,
        sample_project,
        sample_theme,
    ):
        for strategy in all_strategies:
            slide_type = next(iter(strategy.supported_slide_types))
            slide = dict(slide_with_stats, type=slide_type)
            result = strategy.render(slide, sample_project, sample_theme, 7, "pt")
            assert isinstance(result, str)
            assert len(result) > 0

    def test_render_accepts_all_slide_types(
        self,
        all_strategies,
        slide_with_stats,
        sample_project,
        sample_theme,
    ):
        for strategy in all_strategies:
            for slide_type in strategy.supported_slide_types:
                slide = dict(slide_with_stats, type=slide_type)
                result = strategy.render(slide, sample_project, sample_theme, 7, "pt")
                assert isinstance(result, str)

    def test_render_with_empty_heading_does_not_crash(
        self,
        all_strategies,
        slide_with_stats,
        sample_project,
        sample_theme,
    ):
        for strategy in all_strategies:
            slide_type = next(iter(strategy.supported_slide_types))
            slide = dict(slide_with_stats, heading="", type=slide_type)
            result = strategy.render(slide, sample_project, sample_theme, 7, "pt")
            assert isinstance(result, str)

    def test_render_handles_language_parameter(
        self,
        all_strategies,
        slide_with_stats,
        sample_project,
        sample_theme,
    ):
        for strategy in all_strategies:
            slide_type = next(iter(strategy.supported_slide_types))
            slide = dict(slide_with_stats, type=slide_type)
            pt_result = strategy.render(slide, sample_project, sample_theme, 7, "pt")
            en_result = strategy.render(slide, sample_project, sample_theme, 7, "en")
            assert isinstance(pt_result, str)
            assert isinstance(en_result, str)

    def test_render_includes_slide_number(
        self,
        all_strategies,
        slide_with_stats,
        sample_project,
        sample_theme,
    ):
        for strategy in all_strategies:
            slide_type = next(iter(strategy.supported_slide_types))
            slide = dict(slide_with_stats, type=slide_type)
            result = strategy.render(slide, sample_project, sample_theme, 7, "pt")
            assert str(slide["number"]) in result

    def test_strategy_names_are_unique(self, all_strategies):
        names = [s.strategy_name for s in all_strategies]
        assert len(names) == len(set(names))

    def test_strategy_display_names_are_unique(self, all_strategies):
        names = [s.display_name for s in all_strategies]
        assert len(names) == len(set(names))

    def test_render_handles_missing_keys(
        self,
        all_strategies,
        sample_project,
        sample_theme,
    ):
        for strategy in all_strategies:
            slide = {"number": "1", "type": "content"}
            result = strategy.render(slide, sample_project, sample_theme, 7, "pt")
            assert isinstance(result, str)
