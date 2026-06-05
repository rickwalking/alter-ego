"""Neon Shell v2.0 CSS styles for carousel HTML template."""

from rag_backend.application.services.carousel_template.css.base import (
    _get_neon_base_css,
)
from rag_backend.application.services.carousel_template.css.responsive import (
    _get_neon_responsive_css,
)
from rag_backend.application.services.carousel_template.css.slide_styles import (
    _get_neon_slide_css,
)
from rag_backend.application.services.carousel_template.css.styles import (
    get_neon_shell_css,
)

__all__ = [
    "_get_neon_base_css",
    "_get_neon_responsive_css",
    "_get_neon_slide_css",
    "get_neon_shell_css",
]
