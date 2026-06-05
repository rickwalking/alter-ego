"""Feature grid strategy — 2-column feature card grid with icon, title, body.

Renders slides with a heading, body, and a 2-column grid of feature cards.
Falls back to HeroContentStrategy when no features data is available.
"""

from collections.abc import Mapping

from rag_backend.application.services.carousel.types import MAX_FEATURE_ITEMS
from rag_backend.application.services.carousel_template.helpers import _render_inline
from rag_backend.application.services.carousel_template.strategies.hero_content import (
    HeroContentStrategy,
)
from rag_backend.domain.models import CarouselProject

_SUPPORTED_TYPES = frozenset({"content", "closing"})
_FALLBACK = HeroContentStrategy()


class FeatureGridStrategy:
    """Renders slides with heading and a 2-column feature card grid."""

    strategy_name = "feature_grid"
    display_name = "Feature Card Grid"
    supported_slide_types = _SUPPORTED_TYPES

    def render(
        self,
        slide: Mapping[str, object],
        project: CarouselProject,
        theme: Mapping[str, str],
        total_slides: int,
        language: str,
    ) -> str:
        features = slide.get("features")
        if not features or not isinstance(features, list) or not features:
            return _FALLBACK.render(slide, project, theme, total_slides, language)

        heading = _render_inline(str(slide.get("heading") or ""))
        body_raw = str(slide.get("body") or "").strip()
        body_html = (
            f'<p class="body-p">{_render_inline(body_raw)}</p>' if body_raw else ""
        )

        items_html = ""
        for feat in features[:MAX_FEATURE_ITEMS]:
            if not isinstance(feat, dict):
                continue
            icon = _render_inline(str(feat.get("icon") or ""))
            title = _render_inline(str(feat.get("title") or ""))
            feat_body = _render_inline(str(feat.get("body") or ""))
            items_html += (
                f'<div class="feature-item">'
                f'<span class="feature-icon">{icon}</span>'
                f'<div class="feature-text">'
                f'<div class="feature-title">{title}</div>'
                f'<div class="feature-body">{feat_body}</div>'
                f"</div></div>"
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
      <div class="feature-grid cols-2">{items_html}</div>
    </div>
  </div>"""


__all__ = ["FeatureGridStrategy"]
