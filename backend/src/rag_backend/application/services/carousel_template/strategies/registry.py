"""Slide layout strategy registry — maps strategy_name → SlideLayoutStrategy.

Registered at container bootstrap. Strategies are lazy-loaded singletons.
"""

from collections.abc import Mapping

from rag_backend.domain.protocols import (
    SlideLayoutStrategy,
    StrategyNotFoundError,
)

_FALLBACK_STRATEGY = "hero_content"
_INSIGHT_QUOTE_STRATEGY = "insight_quote"
_SUMMARY_GRID_STRATEGY = "summary_grid"
_STAT_CARD_GRID_STRATEGY = "stat_card_grid"
_FEATURE_GRID_STRATEGY = "feature_grid"


class SlideLayoutRegistry:
    """Maps strategy_name → SlideLayoutStrategy implementation."""

    def __init__(self) -> None:
        self._strategies: dict[str, SlideLayoutStrategy] = {}

    def register(self, strategy: SlideLayoutStrategy) -> None:
        """Register a strategy, raising on duplicate names."""
        name = strategy.strategy_name
        if name in self._strategies:
            msg = f"Strategy '{name}' already registered"
            raise ValueError(msg)
        self._strategies[name] = strategy

    def get(self, name: str) -> SlideLayoutStrategy:
        """Retrieve a strategy by name, raising StrategyNotFoundError."""
        strategy = self._strategies.get(name)
        if strategy is None:
            raise StrategyNotFoundError(name)
        return strategy

    def list(self) -> list[dict[str, str]]:
        """List all registered strategies as {name, display_name} dicts."""
        return [
            {"name": s.strategy_name, "display_name": s.display_name}
            for s in self._strategies.values()
        ]

    def find_for_slide(
        self,
        slide_type: str,
        preferred: str | None = None,
        slide: Mapping[str, object] | None = None,
    ) -> SlideLayoutStrategy:
        if preferred:
            strategy = self._strategies.get(preferred)
            if strategy and slide_type in strategy.supported_slide_types:
                return strategy
        if slide is not None:
            structured = self._find_by_structured_content(slide_type, slide)
            if structured is not None:
                return structured
        for strategy in self._strategies.values():
            if slide_type in strategy.supported_slide_types:
                return strategy
        fallback = self._strategies.get(_FALLBACK_STRATEGY)
        if fallback is None:
            msg = f"Fallback strategy {_FALLBACK_STRATEGY!r} not registered"
            raise StrategyNotFoundError(msg)
        return fallback

    def _find_by_structured_content(
        self,
        slide_type: str,
        slide: Mapping[str, object],
    ) -> SlideLayoutStrategy | None:
        """Pick a strategy from structured slide fields before generic fallback."""
        insight = slide.get("insight")
        if isinstance(insight, dict) and insight.get("quote"):
            strategy = self._resolve_structured_strategy(
                slide_type,
                _INSIGHT_QUOTE_STRATEGY,
            )
            if strategy is not None:
                return strategy

        for strategy_name, field_name in (
            (_SUMMARY_GRID_STRATEGY, "summary_points"),
            (_STAT_CARD_GRID_STRATEGY, "stats"),
            (_FEATURE_GRID_STRATEGY, "features"),
        ):
            field = slide.get(field_name)
            if not _has_structured_items(field):
                continue
            strategy = self._resolve_structured_strategy(slide_type, strategy_name)
            if strategy is not None:
                return strategy
        return None

    def _resolve_structured_strategy(
        self,
        slide_type: str,
        strategy_name: str,
    ) -> SlideLayoutStrategy | None:
        strategy = self._strategies.get(strategy_name)
        if strategy is None:
            return None
        if slide_type not in strategy.supported_slide_types:
            return None
        return strategy


def bootstrap_strategies() -> SlideLayoutRegistry:
    """Create and populate the default strategy registry."""
    from rag_backend.application.services.carousel_template.strategies.cta import (
        CtaCenteredStrategy,
    )
    from rag_backend.application.services.carousel_template.strategies.feature_grid import (  # noqa: E501
        FeatureGridStrategy,
    )
    from rag_backend.application.services.carousel_template.strategies.hero_content import (  # noqa: E501
        HeroContentStrategy,
    )
    from rag_backend.application.services.carousel_template.strategies.insight_quote import (  # noqa: E501
        InsightQuoteStrategy,
    )
    from rag_backend.application.services.carousel_template.strategies.intro import (
        IntroHeroStrategy,
    )
    from rag_backend.application.services.carousel_template.strategies.numbered_list import (  # noqa: E501
        NumberedListStrategy,
    )
    from rag_backend.application.services.carousel_template.strategies.stat_card_grid import (  # noqa: E501
        StatCardGridStrategy,
    )
    from rag_backend.application.services.carousel_template.strategies.summary_grid import (  # noqa: E501
        SummaryGridStrategy,
    )

    registry = SlideLayoutRegistry()
    registry.register(IntroHeroStrategy())
    registry.register(HeroContentStrategy())
    registry.register(CtaCenteredStrategy())
    registry.register(StatCardGridStrategy())
    registry.register(FeatureGridStrategy())
    registry.register(InsightQuoteStrategy())
    registry.register(NumberedListStrategy())
    registry.register(SummaryGridStrategy())
    return registry


def _has_structured_items(field: object) -> bool:
    if not isinstance(field, list) or not field:
        return False
    return any(isinstance(item, dict) for item in field)


__all__ = ["SlideLayoutRegistry", "bootstrap_strategies"]
