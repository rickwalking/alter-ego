"""Shared lower-third markup: heading, body and one extra block in the hero shell."""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.application.services.carousel_template.helpers import (
    _render_inline,
    slide_body_html,
)
from rag_backend.application.services.carousel_template.lower_third_shell import (
    LowerThirdConfig,
    artwork_enabled,
    render_lower_third_shell,
)
from rag_backend.domain.protocols.carousel import _RenderOptions


def render_hero_stack(
    slide: Mapping[str, object],
    options: _RenderOptions | None,
    block_html: str,
) -> str:
    """Render heading, body and ``block_html`` in the lower-third shell."""
    total_slides = int(str((options or {}).get("total_slides", 0)))
    heading = _render_inline(str(slide.get("heading") or ""))
    copy_inner = (
        f'<h2 class="slide-hero-heading">{heading}</h2>\n'
        f"      {slide_body_html(slide, 'body-p')}\n"
        f"      {block_html}"
    )
    return render_lower_third_shell(
        LowerThirdConfig(
            slide_number=str(slide["number"]),
            total_slides=total_slides,
            copy_inner_html=copy_inner,
            show_artwork=artwork_enabled(options),
        )
    )


def feature_item_html(icon_html: str, title: str, body: str) -> str:
    """One feature row: ``icon_html`` followed by the inline-rendered title and body."""
    return (
        f'<div class="feature-item">'
        f"{icon_html}"
        f'<div class="feature-text">'
        f'<div class="feature-title">{_render_inline(title)}</div>'
        f'<div class="feature-body">{_render_inline(body)}</div>'
        f"</div></div>"
    )
