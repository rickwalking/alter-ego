"""Stat card grid strategy — 3-column stat cards with value, label, detail.

Renders slides with a heading, body, and a 3-column grid of stat cards.
Falls back to HeroContentStrategy when no stats data is available.
"""

from collections.abc import Mapping

from rag_backend.application.services.carousel.types import MAX_FEATURE_ITEMS
from rag_backend.application.services.carousel_template.helpers import _render_inline
from rag_backend.application.services.carousel_template.strategies.hero_content import (
    HeroContentStrategy,
)
from rag_backend.domain.models import CarouselProject

_SUPPORTED_TYPES = frozenset({"content", "summary"})
_FALLBACK = HeroContentStrategy()


class StatCardGridStrategy:
    """Renders slides with a heading, body, and 3-column stat card grid."""

    strategy_name = "stat_card_grid"
    display_name = "Stat Card Grid"
    supported_slide_types = _SUPPORTED_TYPES

    def render(
        self,
        slide: Mapping[str, object],
        project: CarouselProject,
        theme: Mapping[str, str],
        total_slides: int,
        language: str,
    ) -> str:
        stats = slide.get("stats")
        if not stats or not isinstance(stats, list) or not stats:
            return _FALLBACK.render(slide, project, theme, total_slides, language)

        heading = _render_inline(str(slide.get("heading") or ""))
        body_raw = str(slide.get("body") or "").strip()
        body_html = (
            f'<p class="body-p">{_render_inline(body_raw)}</p>' if body_raw else ""
        )

        cards_html = ""
        for stat in stats[:MAX_FEATURE_ITEMS]:
            if not isinstance(stat, dict):
                continue
            value = _render_inline(str(stat.get("value") or ""))
            label = _render_inline(str(stat.get("label") or ""))
            detail = _render_inline(str(stat.get("detail") or ""))
            detail_html = f'<div class="stat-detail">{detail}</div>' if detail else ""
            cards_html += (
                f'<div class="stat-card">'
                f'<div class="stat-number">{value}</div>'
                f'<div class="stat-label">{label}</div>'
                f"{detail_html}"
                f"</div>"
            )

        return f"""\
  <div class="slide-hero-bg-img">
    <img src="images/slide_{slide["number"]}.jpg" alt="" />
  </div>
  <div class="slide-hero-bg-gradient"></div>
  <div class="slide-hero-content">
    <div class="slide-hero-main">
      <div class="slide-hero-number">0{slide["number"]} / {total_slides:02d}</div>
      <h2 class="slide-hero-heading">{heading}</h2>
      {body_html}
      <div class="stat-row">{cards_html}</div>
    </div>
  </div>"""


__all__ = ["StatCardGridStrategy"]
