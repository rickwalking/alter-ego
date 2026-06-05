"""Carousel HTML template generation and prompt building."""

from rag_backend.application.services.carousel_template.builder import (
    CarouselTemplateBuilder,
)
from rag_backend.application.services.carousel_template.css.styles import (
    get_neon_shell_css,
)
from rag_backend.application.services.carousel_template.design import (
    THEME_PALETTES,
    generate_design_tokens,
)
from rag_backend.application.services.carousel_template.helpers import (
    _render_inline,
)
from rag_backend.application.services.carousel_template.strategies.registry import (
    SlideLayoutRegistry,
    bootstrap_strategies,
)

__all__ = [
    "THEME_PALETTES",
    "CarouselTemplateBuilder",
    "SlideLayoutRegistry",
    "_render_inline",
    "bootstrap_strategies",
    "generate_design_tokens",
    "get_neon_shell_css",
]
