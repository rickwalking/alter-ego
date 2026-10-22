"""Numbered list strategy — 1-based step list from feature data."""

from collections.abc import Mapping

from typing_extensions import override

from rag_backend.application.services.carousel.types import MAX_FEATURE_ITEMS
from rag_backend.application.services.carousel_template.strategies.hero_content import (
    HeroContentStrategy,
)
from rag_backend.application.services.carousel_template.strategies.hero_stack import (
    feature_item_html,
    render_hero_stack,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions

_SUPPORTED_TYPES = frozenset({"content"})
_FALLBACK = HeroContentStrategy()


class NumberedListStrategy:
    """Renders content slides as a numbered step list."""

    strategy_name = "numbered_list"
    display_name = "Numbered List"
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
        features = slide.get("features")
        if not features or not isinstance(features, list) or not features:
            return _FALLBACK.render(slide, project, theme, options=options)

        steps_html = "".join(
            feature_item_html(
                f'<span class="feature-icon numbered-step">{idx}.</span>',
                str(feat.get("title") or ""),
                str(feat.get("body") or ""),
            )
            for idx, feat in enumerate(features[:MAX_FEATURE_ITEMS], start=1)
            if isinstance(feat, dict)
        )
        return render_hero_stack(
            slide, options, f'<div class="feature-grid">{steps_html}</div>'
        )


__all__ = ["NumberedListStrategy"]
