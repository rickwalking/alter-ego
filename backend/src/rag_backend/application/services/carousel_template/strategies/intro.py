"""Intro hero strategy — full-bleed image + gradient + badge + TLDR strip."""

import html
from collections.abc import Mapping

from rag_backend.application.services.carousel_template.helpers import _render_inline
from rag_backend.domain.constants import SWIPE_TEXT_PT
from rag_backend.domain.models import CarouselProject

_SLIDE_TYPE_INTRO = "intro"


class IntroHeroStrategy:
    """Renders the first slide with badge, title, subtitle, and optional TLDR."""

    strategy_name = "intro_hero"
    display_name = "Intro Hero"
    supported_slide_types = frozenset({_SLIDE_TYPE_INTRO})

    def render(
        self,
        slide: Mapping[str, object],
        project: CarouselProject,
        _theme: Mapping[str, str],
        _total_slides: int,
        _language: str,
    ) -> str:
        heading = _render_inline(str(slide.get("heading") or ""))
        subtitle = _render_inline(str(slide.get("body") or ""))
        badge = html.escape(project.niche, quote=True)
        audience = html.escape(project.audience, quote=True)
        tldr = slide.get("tldr_strip")
        tldr_html = ""
        if tldr:
            tldr_html = f'<div class="s1-tldr">{_render_inline(str(tldr))}</div>'
        return f"""\
  <div class="slide-1-bg-img">
    <img src="images/slide_{slide["number"]}.jpg" alt="{heading}" />
  </div>
  <div class="slide-1-bg-gradient"></div>
  <div class="slide-1-content">
    <div class="slide-1-main">
      <div class="s1-badge">
        <span class="s1-badge-dot"></span>
        <span>{badge}</span>
      </div>
      <h1 class="s1-title">{heading}</h1>
      <p class="s1-subtitle">{subtitle}</p>
      {tldr_html}
      <div class="s1-footer">
        <span class="s1-niche">{audience}</span>
        <span class="s1-swipe">{SWIPE_TEXT_PT}</span>
      </div>
    </div>
  </div>"""


__all__ = ["IntroHeroStrategy"]
