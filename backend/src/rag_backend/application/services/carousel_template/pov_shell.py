"""Shared markup for the "Ponto de Vista" layouts (ADR-0021).

No generated artwork: a solid palette background with a subtle texture, the
standard ``.slide-presentation`` / ``.slide-presentation-copy`` /
``.slide-footer`` regions, the slide counter and a footer with the handle.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from rag_backend.application.services.carousel_template.cta_copy import handle_with_at
from rag_backend.application.services.carousel_template.slide_number import (
    format_slide_counter,
)
from rag_backend.domain.constants.carousel_cta import DEFAULT_CTA_HANDLE
from rag_backend.domain.models import CarouselProject


@dataclass(frozen=True)
class PovShellConfig:
    """One POV slide: its number, deck size, copy and optional extras."""

    slide_number: str | int
    total_slides: int
    copy_inner_html: str
    layout: str
    background_html: str = ""
    footer_extra_html: str = ""
    include_counter: bool = True


def handle_html(project: CarouselProject) -> str:
    """The creator handle with ``@``, escaped."""
    handle = project.creator_handle or DEFAULT_CTA_HANDLE
    return html.escape(handle_with_at(handle), quote=True)


def render_pov_shell(config: PovShellConfig, project: CarouselProject) -> str:
    """The solid-background POV slide with the standard presentation regions."""
    counter = ""
    if config.include_counter:
        label = format_slide_counter(config.slide_number, config.total_slides)
        counter = f'<div class="slide-hero-number">{label}</div>'
    return (
        f'  <div class="pov-solid"></div>\n'
        f"  {config.background_html}\n"
        f'  <section class="slide-presentation pov-presentation" '
        f'data-layout="{config.layout}">\n'
        f'    <div class="slide-presentation-copy pov-copy">\n'
        f"      {counter}\n"
        f"      {config.copy_inner_html}\n"
        f"    </div>\n"
        f'    <div class="slide-footer pov-footer">'
        f'<span class="pov-handle">{handle_html(project)}</span>'
        f"{config.footer_extra_html}</div>\n"
        f"  </section>"
    )


__all__ = ["PovShellConfig", "handle_html", "render_pov_shell"]
