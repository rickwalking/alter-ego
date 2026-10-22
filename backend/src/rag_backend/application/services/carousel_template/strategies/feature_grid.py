"""Feature grid strategy — 2-column feature card grid with Lucide icons."""

from collections.abc import Mapping

from typing_extensions import override

from rag_backend.application.services.carousel.types import MAX_FEATURE_ITEMS
from rag_backend.application.services.carousel_template.icon_registry import (
    render_structured_item_icon,
)
from rag_backend.application.services.carousel_template.strategies.hero_content import (
    HeroContentStrategy,
)
from rag_backend.application.services.carousel_template.strategies.hero_stack import (
    feature_item_html,
    render_hero_stack,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions

_SUPPORTED_TYPES = frozenset({"content", "closing"})
_FALLBACK = HeroContentStrategy()


class FeatureGridStrategy:
    """Renders slides with heading and a 2-column feature card grid."""

    strategy_name = "feature_grid"
    display_name = "Feature Card Grid"
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

        items_html = "".join(
            feature_item_html(
                _icon_html(feat),
                str(feat.get("title") or ""),
                str(feat.get("body") or ""),
            )
            for feat in features[:MAX_FEATURE_ITEMS]
            if isinstance(feat, dict)
        )
        return render_hero_stack(
            slide, options, f'<div class="feature-grid cols-2">{items_html}</div>'
        )


def _icon_html(feature: Mapping[str, object]) -> str:
    return f'<span class="feature-icon">{render_structured_item_icon(feature)}</span>'


__all__ = ["FeatureGridStrategy"]
