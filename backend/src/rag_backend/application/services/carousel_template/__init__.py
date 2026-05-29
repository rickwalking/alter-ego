"""Carousel HTML template generation and prompt building."""

from rag_backend.application.services.carousel_template.builder import (
    CarouselTemplateBuilder,
)
from rag_backend.application.services.carousel_template.design import (
    THEME_PALETTES,
    generate_design_tokens,
)
from rag_backend.application.services.carousel_template.helpers import (
    FEATURE_GRID_TWO_COLUMNS,
    _feature_items,
    _insight_quote,
    _render_feature_grid,
    _render_inline,
    _render_insight_card,
    _render_stat_row,
    _stat_items,
)

__all__ = [
    "FEATURE_GRID_TWO_COLUMNS",
    "THEME_PALETTES",
    "CarouselTemplateBuilder",
    "_feature_items",
    "_insight_quote",
    "_render_feature_grid",
    "_render_inline",
    "_render_insight_card",
    "_render_stat_row",
    "_stat_items",
    "generate_design_tokens",
]
