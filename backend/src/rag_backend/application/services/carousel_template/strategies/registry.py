"""Slide layout strategy registry — maps strategy_name → SlideLayoutStrategy.

Registered at container bootstrap. Strategies are lazy-loaded singletons.
"""

from rag_backend.domain.protocols import (
    SlideLayoutStrategy,
    StrategyNotFoundError,
)

_FALLBACK_STRATEGY = "hero_content"


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
        self, slide_type: str, preferred: str | None = None
    ) -> SlideLayoutStrategy:
        if preferred:
            strategy = self._strategies.get(preferred)
            if strategy and slide_type in strategy.supported_slide_types:
                return strategy
        for strategy in self._strategies.values():
            if slide_type in strategy.supported_slide_types:
                return strategy
        fallback = self._strategies.get(_FALLBACK_STRATEGY)
        if fallback is None:
            msg = f"Fallback strategy {_FALLBACK_STRATEGY!r} not registered"
            raise StrategyNotFoundError(msg)
        return fallback


def bootstrap_strategies() -> SlideLayoutRegistry:
    """Create and populate the default strategy registry."""
    from rag_backend.application.services.carousel_template.strategies.cta import (
        CtaCenteredStrategy,
    )
    from rag_backend.application.services.carousel_template.strategies.feature_grid import (
        FeatureGridStrategy,
    )
    from rag_backend.application.services.carousel_template.strategies.hero_content import (
        HeroContentStrategy,
    )
    from rag_backend.application.services.carousel_template.strategies.insight_quote import (
        InsightQuoteStrategy,
    )
    from rag_backend.application.services.carousel_template.strategies.intro import (
        IntroHeroStrategy,
    )
    from rag_backend.application.services.carousel_template.strategies.numbered_list import (
        NumberedListStrategy,
    )
    from rag_backend.application.services.carousel_template.strategies.stat_card_grid import (
        StatCardGridStrategy,
    )

    registry = SlideLayoutRegistry()
    registry.register(IntroHeroStrategy())
    registry.register(HeroContentStrategy())
    registry.register(CtaCenteredStrategy())
    registry.register(StatCardGridStrategy())
    registry.register(FeatureGridStrategy())
    registry.register(InsightQuoteStrategy())
    registry.register(NumberedListStrategy())
    return registry


__all__ = ["SlideLayoutRegistry", "bootstrap_strategies"]
