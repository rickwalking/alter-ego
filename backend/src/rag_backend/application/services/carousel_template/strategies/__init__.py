"""Slide layout strategy implementations.

Each strategy implements the SlideLayoutStrategy Protocol from
domain/protocols/carousel.py and produces inner HTML for a single
carousel slide. Strategies are stateless singletons registered in
SlideLayoutRegistry at container bootstrap.
"""

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

__all__ = [
    "CtaCenteredStrategy",
    "FeatureGridStrategy",
    "HeroContentStrategy",
    "InsightQuoteStrategy",
    "IntroHeroStrategy",
    "NumberedListStrategy",
    "StatCardGridStrategy",
]
