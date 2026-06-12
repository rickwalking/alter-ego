"""Neon Shell v2.0 slide-specific CSS composed from section modules."""

from __future__ import annotations

from rag_backend.application.services.carousel_template.css.slide_styles_closing import (  # noqa: E501
    get_neon_slide_closing_css,
)
from rag_backend.application.services.carousel_template.css.slide_styles_components import (  # noqa: E501
    get_neon_slide_component_css,
)
from rag_backend.application.services.carousel_template.css.slide_styles_shell import (
    get_neon_slide_shell_css,
)


def _get_neon_slide_css(theme: dict[str, str]) -> str:
    """Return slide component CSS matching the reference design."""
    return (
        get_neon_slide_shell_css(theme)
        + get_neon_slide_component_css(theme)
        + get_neon_slide_closing_css(theme)
    )


__all__ = ["_get_neon_slide_css"]
