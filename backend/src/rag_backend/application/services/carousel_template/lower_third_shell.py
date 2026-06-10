"""Shared lower-third presentation shell markup for slides 1 through 6."""

from __future__ import annotations

import html

from rag_backend.application.services.carousel_template.slide_number import (
    normalize_slide_number,
)


def render_slide_artwork(slide_number: str | int, *, alt: str = "") -> str:
    """Render the full-bleed artwork region for a slide."""
    safe_number = normalize_slide_number(slide_number)
    safe_alt = html.escape(alt, quote=True)
    return (
        f'  <div class="slide-artwork">\n'
        f'    <img src="images/slide_{safe_number}.jpg" alt="{safe_alt}" />\n'
        f"  </div>"
    )


def render_lower_third_shell(
    *,
    slide_number: str | int,
    total_slides: int,
    copy_inner_html: str,
    artwork_alt: str = "",
    overlay_classes: str = "slide-overlay",
    footer_html: str = "",
    include_counter: bool = True,
) -> str:
    """Render the shared lower-third shell used by slides 1 through 6."""
    safe_number = normalize_slide_number(slide_number)
    counter_html = ""
    if include_counter:
        counter_html = (
            f'<div class="slide-hero-number">0{safe_number} / {total_slides:02d}</div>'
        )
    return (
        f"{render_slide_artwork(safe_number, alt=artwork_alt)}\n"
        f'  <div class="{overlay_classes}"></div>\n'
        f'  <section class="slide-presentation" data-layout="lower-third">\n'
        f'    <div class="slide-presentation-copy slide-hero-main">\n'
        f"      {counter_html}\n"
        f"      {copy_inner_html}\n"
        f"    </div>\n"
        f"    {footer_html}\n"
        f"  </section>"
    )


__all__ = ["render_lower_third_shell", "render_slide_artwork"]
