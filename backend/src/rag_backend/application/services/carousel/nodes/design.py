"""Phase 4: design system.

Resolves the color theme, stamps design tokens onto the project, and
builds the PT HTML carousel string. Shared helper `resolve_theme` is
also used by the image-generation node so the vendor strategy gets the
same palette the template will render against.
"""

from __future__ import annotations

from typing import Any

from rag_backend.application.services.carousel.types import SlideData
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.domain.constants import CAROUSEL_THEMES
from rag_backend.domain.models import CarouselProject, CarouselTheme

DEFAULT_THEME_KEY = "ai_competition"


def resolve_theme(project: CarouselProject) -> dict[str, str]:
    """Pick the color theme for this project, falling back on the default."""
    if project.theme != CarouselTheme.AUTO:
        return CAROUSEL_THEMES.get(project.theme.value, CAROUSEL_THEMES[DEFAULT_THEME_KEY])
    return CAROUSEL_THEMES[DEFAULT_THEME_KEY]


def run_design(
    project: CarouselProject,
    slides: list[SlideData],
    *,
    template: CarouselTemplateBuilder,
) -> str:
    """Resolve theme, stamp design tokens on the project, and build HTML."""
    theme = resolve_theme(project)
    project.set_theme_colors(
        primary=theme["primary"],
        accent=theme["accent"],
        background=theme["background"],
    )

    project.design_tokens = CarouselTemplateBuilder.generate_design_tokens(project)

    slide_dicts: list[dict[str, Any]] = [
        {
            "number": str(s.slide_number),
            "type": s.slide_type,
            "heading": s.heading,
            "body": s.body,
            "features": s.features,
            "stats": s.stats,
            "insight": s.insight,
        }
        for s in slides
    ]
    return template.build_carousel_html(project, slide_dicts, theme)
