"""Cover-card strategy: slide 1 as a framed GrokBot screenshot (AE-0418).

The owner chose a ``screenshot`` cover (a post, product shot or logo) on
Telegram. It renders on the deck's solid background: the title on top, the
image as a rounded, shadowed card in the middle (aspect kept, never cropped)
and a small source credit under it (``@handle · X`` or the domain). Used by
every mode; an ``ai_image`` cover renders in the hook / intro layouts instead.
"""

from __future__ import annotations

import html
from collections.abc import Mapping

from typing_extensions import override

from rag_backend.application.services.carousel_template.constants import swipe_text_for
from rag_backend.application.services.carousel_template.helpers import (
    _plain_text_for_attribute,
    _render_inline,
)
from rag_backend.application.services.carousel_template.pov_shell import (
    PovShellConfig,
    render_pov_shell,
)
from rag_backend.application.services.carousel_template.strategies.intro import (
    IntroHeroStrategy,
)
from rag_backend.application.services.carousel_template.strategies.photo_errors import (
    slide_cover_src,
)
from rag_backend.domain.constants import LANGUAGE_PT
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions

COVER_CARD_STRATEGY = "cover_card"
_LAYOUT = "cover-card"
_FIRST_SLIDE = 1


def cover_card_strategy(
    project: CarouselProject, slide: Mapping[str, object]
) -> str | None:
    """``cover_card`` for slide 1 of a deck whose chosen cover is a screenshot."""
    cover = project.slide_cover
    if cover is None or not cover.is_screenshot:
        return None
    if str(slide.get("number", "")) != str(_FIRST_SLIDE):
        return None
    return COVER_CARD_STRATEGY


def _card_html(project: CarouselProject, alt: str) -> str:
    src = slide_cover_src(project) or ""
    credit = project.slide_cover.credit if project.slide_cover else ""
    credit_html = (
        f'<figcaption class="cover-card-credit">{html.escape(credit)}</figcaption>'
        if credit
        else ""
    )
    return (
        f'<figure class="cover-card-frame">'
        f'<img src="{html.escape(src, quote=True)}" '
        f'alt="{html.escape(_plain_text_for_attribute(alt), quote=True)}" />'
        f"{credit_html}</figure>"
    )


class CoverCardStrategy:
    """Slide 1 with the title above a framed screenshot and its credit."""

    strategy_name = COVER_CARD_STRATEGY
    display_name = "Cover Card"
    supported_slide_types = frozenset({"intro"})

    @override
    def render(
        self,
        slide: Mapping[str, object],
        project: CarouselProject,
        _theme: Mapping[str, str],
        *,
        options: _RenderOptions | None = None,
    ) -> str:
        cover = project.slide_cover
        if cover is None or not cover.is_screenshot:
            # Picked by name without a screenshot cover: the default slide 1.
            return IntroHeroStrategy().render(slide, project, _theme, options=options)
        opts = options or {}
        language = str(opts.get("language", LANGUAGE_PT))
        heading = str(slide.get("heading") or "")
        return render_pov_shell(
            PovShellConfig(
                slide_number=str(slide.get("number", _FIRST_SLIDE)),
                total_slides=int(str(opts.get("total_slides", 0))),
                copy_inner_html=(
                    f'<h1 class="cover-card-heading">{_render_inline(heading)}</h1>'
                ),
                layout=_LAYOUT,
                background_html=_card_html(project, heading),
                footer_extra_html=(
                    f'<span class="s1-swipe">{swipe_text_for(language)}</span>'
                ),
                include_counter=False,
            ),
            project,
        )


__all__ = ["COVER_CARD_STRATEGY", "CoverCardStrategy", "cover_card_strategy"]
