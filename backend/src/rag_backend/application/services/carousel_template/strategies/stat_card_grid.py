"""Stat card grid strategy — 3-column stat cards."""

from collections.abc import Mapping

from typing_extensions import override

from rag_backend.application.services.carousel.types import MAX_FEATURE_ITEMS
from rag_backend.application.services.carousel_template.helpers import (
    _render_inline,
)
from rag_backend.application.services.carousel_template.strategies.hero_content import (
    HeroContentStrategy,
)
from rag_backend.application.services.carousel_template.strategies.hero_stack import (
    render_hero_stack,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions

_SUPPORTED_TYPES = frozenset({"content", "summary"})
_FALLBACK = HeroContentStrategy()


class StatCardGridStrategy:
    """Renders slides with a heading, body, and 3-column stat card grid."""

    strategy_name = "stat_card_grid"
    display_name = "Stat Card Grid"
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
        stats = slide.get("stats")
        if not stats or not isinstance(stats, list) or not stats:
            return _FALLBACK.render(slide, project, theme, options=options)

        return render_hero_stack(
            slide,
            options,
            f'<div class="stat-row">{_build_stat_cards(stats)}</div>',
        )


def _build_stat_cards(stats: object) -> str:
    cards_html = ""
    if not isinstance(stats, list):
        return cards_html
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
    return cards_html


__all__ = ["StatCardGridStrategy"]
