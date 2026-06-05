"""CTA centered strategy — centered avatar + name + handle + follow CTA.

Wraps content in hero-bg image + gradient for visual continuity with slides 1-6
(P1). On carousels with fewer than 7 slides, falls back to plain dark background
to avoid forcing a hero-bg on a very short carousel.
"""

import html
from collections.abc import Mapping

from rag_backend.domain.constants import LANGUAGE_EN
from rag_backend.domain.models import CarouselProject

_SLIDE_TYPE_CTA = "cta"
_MIN_SLIDES_FOR_HERO_BG = 7


class CtaCenteredStrategy:
    """Renders the final CTA slide with creator avatar, name, handle, and follow CTA."""

    strategy_name = "cta_centered"
    display_name = "CTA Centered"
    supported_slide_types = frozenset({_SLIDE_TYPE_CTA})

    def render(
        self,
        slide: Mapping[str, object],
        project: CarouselProject,
        _theme: Mapping[str, str],
        total_slides: int,
        language: str,
    ) -> str:
        name = html.escape(project.creator_name or "", quote=True) if project else ""
        handle = project.creator_handle or "" if project else ""
        avatar = project.creator_avatar_url or "" if project else ""
        handle_text = f"@{handle}" if handle else ""
        handle_html = (
            f'<div class="closing-handle">{html.escape(handle_text, quote=True)}</div>'
            if handle_text
            else ""
        )
        avatar_html = (
            f'<div class="closing-avatar">'
            f'<img src="{html.escape(avatar, quote=True)}" alt="{name}" />'
            f"</div>"
            if avatar
            else ""
        )
        if language == LANGUAGE_EN:
            cta_text = "Follow for more content like this"
        else:
            cta_text = "Siga para mais conteúdo como esse"
        slide_number = str(slide.get("number", ""))
        inner = f"""\
  <div class="slide-content slide-closing">
    <div class="slide-number">0{slide_number} / {total_slides:02d}</div>
    {avatar_html}
    <div class="closing-name">{name}</div>
    {handle_html}
    <div class="closing-cta">{cta_text}</div>
  </div>"""
        if total_slides >= _MIN_SLIDES_FOR_HERO_BG:
            return f"""\
  <div class="slide-hero-bg-img">
    <img src="images/slide_{slide_number}.jpg" alt="" />
  </div>
  <div class="slide-hero-bg-gradient"></div>
  <div class="slide-hero-content is-centered">
    {inner.strip()}
  </div>"""
        return inner


__all__ = ["CtaCenteredStrategy"]
