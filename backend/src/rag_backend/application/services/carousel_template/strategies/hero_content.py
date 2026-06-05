"""Hero content strategy — background image + gradient + heading + body.

Used for content, summary, and closing-type slides. Reads heading and body
from the slide dict and renders them in the hero-bg layout. This is the
default fallback strategy when no structured data (features, stats, insight)
is available.

Watermark appears only on slide 2 (P2). Slide 2 also shows directional swipe
text (P5). The watermark utility is shared with html_template (AC 4).
"""

from collections.abc import Mapping

from rag_backend.application.services.carousel_template.helpers import (
    _build_watermark_html,
    _render_inline,
)
from rag_backend.domain.constants import LANGUAGE_EN
from rag_backend.domain.models import CarouselProject

_SUPPORTED_TYPES = frozenset({"content", "summary", "closing"})
_WATERMARK_SLIDE_NUMBER = "2"
_SWIPE_TEXT_PT = "Deslize →"
_SWIPE_TEXT_EN = "Swipe →"


class HeroContentStrategy:
    """Renders a slide with hero background image, heading, and body text."""

    strategy_name = "hero_content"
    display_name = "Hero Content"
    supported_slide_types = _SUPPORTED_TYPES

    def render(
        self,
        slide: Mapping[str, object],
        project: CarouselProject,
        _theme: Mapping[str, str],
        total_slides: int,
        language: str,
    ) -> str:
        heading = _render_inline(str(slide.get("heading") or ""))
        body_raw = str(slide.get("body") or "").strip()
        slide_number = str(slide.get("number", ""))
        show_watermark = slide_number == _WATERMARK_SLIDE_NUMBER
        watermark_html = _build_watermark_html(project) if show_watermark else ""
        show_swipe = slide_number == _WATERMARK_SLIDE_NUMBER
        swipe_text = _SWIPE_TEXT_EN if language == LANGUAGE_EN else _SWIPE_TEXT_PT
        swipe_html = f'<div class="s1-swipe">{swipe_text}</div>' if show_swipe else ""
        body_html = (
            f'<p class="slide-hero-body">{_render_inline(body_raw)}</p>'
            if body_raw
            else ""
        )
        return f"""\
  <div class="slide-hero-bg-img">
    <img src="images/slide_{slide_number}.jpg" alt="" />
  </div>
  <div class="slide-hero-bg-gradient"></div>
  <div class="slide-hero-content">
    <div class="slide-hero-main">
      <div class="slide-hero-number">0{slide_number} / {total_slides:02d}</div>
      <h2 class="slide-hero-heading">{heading}</h2>
      {body_html}
    </div>
    {swipe_html}
    {watermark_html}
  </div>"""


__all__ = ["HeroContentStrategy"]
