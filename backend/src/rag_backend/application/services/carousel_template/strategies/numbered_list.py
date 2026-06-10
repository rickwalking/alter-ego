"""Numbered list strategy — 1-based step list from feature data."""

from collections.abc import Mapping

from rag_backend.application.services.carousel.types import MAX_FEATURE_ITEMS
from rag_backend.application.services.carousel_template.helpers import _render_inline
from rag_backend.application.services.carousel_template.lower_third_shell import (
    render_lower_third_shell,
)
from rag_backend.application.services.carousel_template.strategies.hero_content import (
    HeroContentStrategy,
)
from rag_backend.domain.models import CarouselProject

_SUPPORTED_TYPES = frozenset({"content"})
_FALLBACK = HeroContentStrategy()


class NumberedListStrategy:
    """Renders content slides as a numbered step list."""

    strategy_name = "numbered_list"
    display_name = "Numbered List"
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
        slide_number = str(slide["number"])

        steps_html = ""
        for idx, feat in enumerate(features[:MAX_FEATURE_ITEMS], start=1):
            if not isinstance(feat, dict):
                continue
            title = _render_inline(str(feat.get("title") or ""))
            feat_body = _render_inline(str(feat.get("body") or ""))
            steps_html += (
                f'<div class="feature-item">'
                f'<span class="feature-icon numbered-step">{idx}.</span>'
                f'<div class="feature-text">'
                f'<div class="feature-title">{title}</div>'
                f'<div class="feature-body">{feat_body}</div>'
                f"</div></div>"
            )

        copy_inner = (
            f'<h2 class="slide-hero-heading">{heading}</h2>\n'
            f"      {body_html}\n"
            f'      <div class="feature-grid">{steps_html}</div>'
        )
        return render_lower_third_shell(
            slide_number=slide_number,
            total_slides=total_slides,
            copy_inner_html=copy_inner,
        )


__all__ = ["NumberedListStrategy"]
