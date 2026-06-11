"""Hero content strategy — lower-third shell with heading and body text."""

from collections.abc import Mapping

from typing_extensions import override

from rag_backend.application.services.carousel_template.constants import SWIPE_TEXT
from rag_backend.application.services.carousel_template.helpers import (
    _build_watermark_html,
    _render_inline,
)
from rag_backend.application.services.carousel_template.lower_third_shell import (
    LowerThirdConfig,
    render_lower_third_shell,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions

_SUPPORTED_TYPES = frozenset({"content", "summary", "closing"})
_WATERMARK_SLIDE_NUMBER = "2"


class HeroContentStrategy:
    """Renders a slide with hero background image, heading, and body text."""

    strategy_name = "hero_content"
    display_name = "Hero Content"
    supported_slide_types = _SUPPORTED_TYPES

    @override
    def render(
        self,
        slide: Mapping[str, object],
        project: CarouselProject,
        _theme: Mapping[str, str],
        *,
        options: _RenderOptions | None = None,
    ) -> str:
        opts = options or {}
        total_slides: int = opts.get("total_slides", 0)  # type: ignore[assignment]
        heading = _render_inline(str(slide.get("heading") or ""))
        body_raw = str(slide.get("body") or "").strip()
        slide_number = str(slide.get("number", ""))
        show_watermark = slide_number == _WATERMARK_SLIDE_NUMBER
        watermark_html = _build_watermark_html(project) if show_watermark else ""
        show_swipe = slide_number == _WATERMARK_SLIDE_NUMBER
        swipe_html = f'<div class="s1-swipe">{SWIPE_TEXT}</div>' if show_swipe else ""
        body_html = (
            f'<p class="slide-hero-body">{_render_inline(body_raw)}</p>'
            if body_raw
            else ""
        )
        copy_inner = f'<h2 class="slide-hero-heading">{heading}</h2>\n      {body_html}'
        footer_html = "\n".join(part for part in (swipe_html, watermark_html) if part)
        return render_lower_third_shell(
            LowerThirdConfig(
                slide_number=slide_number,
                total_slides=total_slides,
                copy_inner_html=copy_inner,
                artwork_alt=heading,
                footer_html=footer_html,
            )
        )


__all__ = ["HeroContentStrategy"]
