"""Insight quote strategy — accent-bordered quote card with attribution.

A ``pov_news`` card (a quoted account with ``name`` and ``handle``)
renders on the POV statement shell with the attribution row of
``news_quote``; every other card keeps today's lower-third layout.
"""

from collections.abc import Mapping

from typing_extensions import override

from rag_backend.application.services.carousel_template.helpers import (
    _render_inline,
    slide_body_html,
)
from rag_backend.application.services.carousel_template.pov_shell import (
    PovShellConfig,
    render_pov_shell,
)
from rag_backend.application.services.carousel_template.strategies import news_quote
from rag_backend.application.services.carousel_template.strategies.hero_content import (
    HeroContentStrategy,
)
from rag_backend.application.services.carousel_template.strategies.hero_stack import (
    render_hero_stack,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions

INSIGHT_QUOTE_STRATEGY = "insight_quote"
_SUPPORTED_TYPES = frozenset({"content", "closing"})
_FALLBACK = HeroContentStrategy()
_NEWS_QUOTE_LAYOUT = "pov-quote"


class InsightQuoteStrategy:
    """Renders slides with heading and an accent-bordered insight quote card."""

    strategy_name = INSIGHT_QUOTE_STRATEGY
    display_name = "Insight Quote"
    supported_slide_types = _SUPPORTED_TYPES

    @override
    def render(
        self,
        slide: Mapping[str, object],
        project: CarouselProject,
        theme: Mapping[str, str],
        *,
        options: _RenderOptions | None = None,
    ) -> str:
        opts = options or {}
        total_slides: int = opts.get("total_slides", 0)  # type: ignore[assignment]
        insight = slide.get("insight")
        if not insight or not isinstance(insight, dict):
            return _FALLBACK.render(slide, project, theme, options=options)
        if news_quote.is_news_quote(insight):
            return _render_news_quote(slide, project, total_slides)

        quote = _render_inline(str(insight.get("quote") or ""))
        attribution = _render_inline(str(insight.get("attribution") or ""))
        if not quote:
            return _FALLBACK.render(slide, project, theme, options=options)

        attribution_html = (
            f'<span class="insight-attribution">— {attribution}</span>'
            if attribution
            else ""
        )
        return render_hero_stack(
            slide,
            options,
            f'<div class="insight-card">{quote}{attribution_html}</div>',
        )


def _render_news_quote(
    slide: Mapping[str, object], project: CarouselProject, total_slides: int
) -> str:
    """Heading, body and the verified quote card on the POV shell."""
    insight = slide.get("insight")
    card = news_quote.news_quote_card_html(insight) if isinstance(insight, dict) else ""
    heading = _render_inline(str(slide.get("heading") or ""))
    body_html = slide_body_html(slide, "pov-statement-body")
    return render_pov_shell(
        PovShellConfig(
            slide_number=str(slide.get("number", "")),
            total_slides=total_slides,
            copy_inner_html=(
                f'<h2 class="pov-statement-heading">{heading}</h2>\n'
                f"      {body_html}\n      {card}"
            ),
            layout=_NEWS_QUOTE_LAYOUT,
        ),
        project,
    )


__all__ = ["INSIGHT_QUOTE_STRATEGY", "InsightQuoteStrategy"]
