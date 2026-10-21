"""Shared lower-third presentation shell markup for slides 1 through 6."""

from __future__ import annotations

import html
from dataclasses import dataclass

from rag_backend.application.services.carousel_template.helpers import (
    _plain_text_for_attribute,
)
from rag_backend.application.services.carousel_template.slide_number import (
    format_slide_counter,
    normalize_slide_number,
)
from rag_backend.domain.protocols.carousel import _RenderOptions

_NO_ARTWORK_HTML = (
    '  <div class="slide-artwork slide-artwork-none" aria-hidden="true"></div>'
)


def render_slide_artwork(
    slide_number: str | int, *, alt: str = "", src: str | None = None
) -> str:
    """Render the full-bleed artwork region for a slide.

    ``src`` replaces the generated hero (a GrokBot ``ai_image`` cover).
    """
    safe_number = normalize_slide_number(slide_number)
    safe_alt = html.escape(_plain_text_for_attribute(alt), quote=True)
    image = html.escape(src or f"images/slide_{safe_number}.jpg", quote=True)
    return (
        f'  <div class="slide-artwork">\n'
        f'    <img src="{image}" alt="{safe_alt}" />\n'
        f"  </div>"
    )


@dataclass(frozen=True)
class LowerThirdConfig:
    slide_number: str | int
    total_slides: int
    copy_inner_html: str
    artwork_alt: str = ""
    overlay_classes: str = "slide-overlay"
    footer_html: str = ""
    include_counter: bool = True
    artwork_src: str | None = None
    show_artwork: bool = True


def artwork_enabled(options: _RenderOptions | None) -> bool:
    """Whether the slide being rendered gets generated artwork."""
    return (options or {}).get("artwork", True)


def render_lower_third_shell(
    config: LowerThirdConfig,
) -> str:
    """Render the shared lower-third shell used by slides 1 through 6."""
    safe_number = normalize_slide_number(config.slide_number)
    counter_html = ""
    if config.include_counter:
        counter = format_slide_counter(safe_number, config.total_slides)
        counter_html = f'<div class="slide-hero-number">{counter}</div>'
    return (
        f"{_artwork(safe_number, config)}\n"
        f'  <div class="{config.overlay_classes}"></div>\n'
        f'  <section class="slide-presentation" data-layout="lower-third">\n'
        f'    <div class="slide-presentation-copy slide-hero-main">\n'
        f"      {counter_html}\n"
        f"      {config.copy_inner_html}\n"
        f"    </div>\n"
        f"    {config.footer_html}\n"
        f"  </section>"
    )


def _artwork(safe_number: str, config: LowerThirdConfig) -> str:
    """A slide the images phase does not plan never references ``images/slide_N.jpg``;
    an explicit ``artwork_src`` (the GrokBot cover) still wins.
    """
    if not config.show_artwork and config.artwork_src is None:
        return _NO_ARTWORK_HTML
    return render_slide_artwork(
        safe_number, alt=config.artwork_alt, src=config.artwork_src
    )


__all__ = [
    "LowerThirdConfig",
    "artwork_enabled",
    "render_lower_third_shell",
    "render_slide_artwork",
]
