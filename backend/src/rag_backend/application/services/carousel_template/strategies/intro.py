"""Intro hero strategy — lower-third shell with badge, title, subtitle, TLDR."""

import html
from collections.abc import Mapping

from typing_extensions import override

from rag_backend.application.services.carousel_template.helpers import _render_inline
from rag_backend.application.services.carousel_template.lower_third_shell import (
    LowerThirdConfig,
    render_lower_third_shell,
)
from rag_backend.domain.constants import SWIPE_TEXT_PT
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions

_SLIDE_TYPE_INTRO = "intro"


class IntroHeroStrategy:
    """Renders the first slide with badge, title, subtitle, and optional TLDR."""

    strategy_name = "intro_hero"
    display_name = "Intro Hero"
    supported_slide_types = frozenset({_SLIDE_TYPE_INTRO})

    @override
    def render(
        self,
        slide: Mapping[str, object],
        project: CarouselProject,
        _theme: Mapping[str, str],
        *,
        options: _RenderOptions | None = None,
    ) -> str:
        opts = options or {}
        total_slides: int = opts.get("total_slides", 0)  # type: ignore[assignment]
        heading = _render_inline(str(slide.get("heading") or ""))
        subtitle = _render_inline(str(slide.get("body") or ""))
        badge = html.escape(project.niche, quote=True)
        audience = html.escape(project.audience, quote=True)
        tldr = slide.get("tldr_strip")
        tldr_html = ""
        if tldr:
            tldr_html = f'<div class="s1-tldr">{_render_inline(str(tldr))}</div>'
        slide_number = str(slide.get("number", "1"))
        copy_inner = (
            f'<div class="s1-badge">'
            f'<span class="s1-badge-dot"></span>'
            f"<span>{badge}</span>"
            f"</div>\n"
            f'      <h1 class="s1-title">{heading}</h1>\n'
            f'      <p class="s1-subtitle">{subtitle}</p>\n'
            f"      {tldr_html}"
        )
        footer_html = (
            f'<div class="s1-footer">'
            f'<span class="s1-niche">{audience}</span>'
            f'<span class="s1-swipe">{SWIPE_TEXT_PT}</span>'
            f"</div>"
        )
        return render_lower_third_shell(
            LowerThirdConfig(
                slide_number=slide_number,
                total_slides=total_slides,
                copy_inner_html=copy_inner,
                artwork_alt=heading,
                overlay_classes="slide-overlay slide-1-bg-gradient",
                footer_html=footer_html,
                include_counter=False,
            )
        )


__all__ = ["IntroHeroStrategy"]
