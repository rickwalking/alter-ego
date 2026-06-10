"""Insight quote strategy — accent-bordered quote card with attribution."""

from collections.abc import Mapping

from rag_backend.application.services.carousel_template.helpers import _render_inline
from rag_backend.application.services.carousel_template.lower_third_shell import (
    render_lower_third_shell,
)
from rag_backend.application.services.carousel_template.strategies.hero_content import (
    HeroContentStrategy,
)
from rag_backend.domain.models import CarouselProject

_SUPPORTED_TYPES = frozenset({"content", "closing"})
_FALLBACK = HeroContentStrategy()


class InsightQuoteStrategy:
    """Renders slides with heading and an accent-bordered insight quote card."""

    strategy_name = "insight_quote"
    display_name = "Insight Quote"
    supported_slide_types = _SUPPORTED_TYPES

    def render(
        self,
        slide: Mapping[str, object],
        project: CarouselProject,
        theme: Mapping[str, str],
        total_slides: int,
        language: str,
    ) -> str:
        insight = slide.get("insight")
        if not insight or not isinstance(insight, dict):
            return _FALLBACK.render(slide, project, theme, total_slides, language)

        quote = _render_inline(str(insight.get("quote") or ""))
        attribution = _render_inline(str(insight.get("attribution") or ""))
        if not quote:
            return _FALLBACK.render(slide, project, theme, total_slides, language)

        heading = _render_inline(str(slide.get("heading") or ""))
        body_raw = str(slide.get("body") or "").strip()
        body_html = (
            f'<p class="body-p">{_render_inline(body_raw)}</p>' if body_raw else ""
        )
        attribution_html = (
            f'<span class="insight-attribution">— {attribution}</span>'
            if attribution
            else ""
        )
        slide_number = str(slide["number"])
        copy_inner = (
            f'<h2 class="slide-hero-heading">{heading}</h2>\n'
            f"      {body_html}\n"
            f'      <div class="insight-card">{quote}{attribution_html}</div>'
        )
        return render_lower_third_shell(
            slide_number=slide_number,
            total_slides=total_slides,
            copy_inner_html=copy_inner,
        )


__all__ = ["InsightQuoteStrategy"]
