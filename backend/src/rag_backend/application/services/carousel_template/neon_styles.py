"""Neon Shell v2.0 CSS styles for carousel HTML template."""

from __future__ import annotations

from rag_backend.application.services.carousel_template.neon_base import (
    _get_neon_base_css,
)
from rag_backend.application.services.carousel_template.neon_responsive import (
    _get_neon_responsive_css,
)
from rag_backend.application.services.carousel_template.neon_slide_styles import (
    _get_neon_slide_css,
)


def get_neon_shell_css(theme: dict[str, str]) -> str:
    """Return the complete Neon Shell v2.0 CSS string for the given theme."""
    return (
        _get_neon_base_css(theme)
        + _get_neon_slide_css(theme)
        + _get_neon_responsive_css()
    )


__all__ = ["get_neon_shell_css"]
