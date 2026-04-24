"""Phase 4: design system.

Resolves the color theme, stamps design tokens onto the project, and
builds the PT HTML carousel string. Shared helper ``resolve_theme`` is
also used by the image-generation node so the vendor strategy gets the
same palette the template will render against.
"""

from __future__ import annotations

from pathlib import Path

from rag_backend.application.services.carousel.theme_resolver import (
    resolve_theme,
)
from rag_backend.application.services.carousel.types import SlideData, SlideDict
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.domain.models import CarouselProject

OVERRIDES_FILENAME = "design_overrides.css"


def _read_design_overrides(output_dir: str | None) -> str | None:
    """Read per-project CSS overrides from disk if present."""
    if not output_dir:
        return None
    path = Path(output_dir) / OVERRIDES_FILENAME
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


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

    slide_dicts: list[SlideDict] = [
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

    overrides = _read_design_overrides(project.output_dir)

    return template.build_carousel_html(project, slide_dicts, theme, design_overrides=overrides)
