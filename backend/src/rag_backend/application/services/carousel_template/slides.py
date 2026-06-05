"""Individual slide renderers for carousel HTML matching Neon Shell v2.0 reference."""

import html

from rag_backend.application.services.carousel.types import SlideDict
from rag_backend.application.services.carousel_template.helpers import (
    _render_inline,
)
from rag_backend.domain.constants import SWIPE_TEXT_PT
from rag_backend.domain.models import CarouselProject


def _render_intro_slide(
    slide: SlideDict, project: CarouselProject, _theme: dict[str, str]
) -> str:
    """Render intro slide matching reference structure."""
    heading = _render_inline(str(slide["heading"]))
    subtitle = _render_inline(str(slide["body"]))
    badge = html.escape(project.niche, quote=True)
    audience = html.escape(project.audience, quote=True)
    tldr = slide.get("tldr_strip")
    tldr_html = ""
    if tldr:
        tldr_html = f'<div class="s1-tldr">{_render_inline(str(tldr))}</div>'
    return f"""\
  <div class="slide-1-bg-img">
    <img src="images/slide_{slide["number"]}.jpg" alt="{heading}" />
  </div>
  <div class="slide-1-bg-gradient"></div>
  <div class="slide-1-content">
    <div class="slide-1-main">
      <div class="s1-badge">
        <span class="s1-badge-dot"></span>
        <span>{badge}</span>
      </div>
      <h1 class="s1-title">{heading}</h1>
      <p class="s1-subtitle">{subtitle}</p>
      {tldr_html}
      <div class="s1-footer">
        <span class="s1-niche">{audience}</span>
        <span class="s1-swipe">{SWIPE_TEXT_PT}</span>
      </div>
    </div>
  </div>"""


def _render_summary_slide(
    slide: SlideDict,
    _theme: dict[str, str],
    total_slides: int = 6,
    watermark_html: str = "",
) -> str:
    """Render summary slide with hero-bg layout."""
    heading = _render_inline(str(slide["heading"]))
    body_raw = str(slide.get("body") or "").strip()
    body_html = (
        f'<p class="slide-hero-body">{_render_inline(body_raw)}</p>' if body_raw else ""
    )
    return f"""\
  <div class="slide-hero-bg-img">
    <img src="images/slide_{slide["number"]}.jpg" alt="" />
  </div>
  <div class="slide-hero-bg-gradient"></div>
  <div class="slide-hero-content">
    <div class="slide-hero-main">
      <div class="slide-hero-number">0{slide["number"]} / {total_slides:02d}</div>
      <h2 class="slide-hero-heading">{heading}</h2>
      {body_html}
    </div>
    {watermark_html}
  </div>"""


def _render_content_slide(
    slide: SlideDict,
    _theme: dict[str, str],
    total_slides: int = 6,
    watermark_html: str = "",
) -> str:
    """Render content slide with hero-bg layout."""
    heading = _render_inline(str(slide["heading"]))
    body_raw = str(slide.get("body") or "").strip()
    body_html = (
        f'<p class="slide-hero-body">{_render_inline(body_raw)}</p>' if body_raw else ""
    )
    return f"""\
  <div class="slide-hero-bg-img">
    <img src="images/slide_{slide["number"]}.jpg" alt="" />
  </div>
  <div class="slide-hero-bg-gradient"></div>
  <div class="slide-hero-content">
    <div class="slide-hero-main">
      <div class="slide-hero-number">0{slide["number"]} / {total_slides:02d}</div>
      <h2 class="slide-hero-heading">{heading}</h2>
      {body_html}
    </div>
    {watermark_html}
  </div>"""


def _render_closing_slide(
    slide: SlideDict,
    _theme: dict[str, str],
    total_slides: int = 6,
    watermark_html: str = "",
) -> str:
    """Render closing slide with hero-bg layout."""
    heading = _render_inline(str(slide["heading"]))
    body_raw = str(slide.get("body") or "").strip()
    body_html = (
        f'<p class="slide-hero-body">{_render_inline(body_raw)}</p>' if body_raw else ""
    )
    return f"""\
  <div class="slide-hero-bg-img">
    <img src="images/slide_{slide["number"]}.jpg" alt="" />
  </div>
  <div class="slide-hero-bg-gradient"></div>
  <div class="slide-hero-content">
    <div class="slide-hero-main">
      <div class="slide-hero-number">0{slide["number"]} / {total_slides:02d}</div>
      <h2 class="slide-hero-heading">{heading}</h2>
      {body_html}
    </div>
    {watermark_html}
  </div>"""


def _render_cta_slide(
    slide: SlideDict,
    _theme: dict[str, str],
    language: str = "pt",
    total_slides: int = 6,
    project: CarouselProject | None = None,
) -> str:
    """Render closing/CTA slide with centered avatar layout."""
    from rag_backend.domain.constants import LANGUAGE_EN

    name = html.escape(project.creator_name or "", quote=True) if project else ""
    handle = project.creator_handle or "" if project else ""
    avatar = project.creator_avatar_url or "" if project else ""
    handle_text = f"@{handle}" if handle else ""
    handle_html = (
        f'<div class="closing-handle">{html.escape(handle_text, quote=True)}</div>'
        if handle_text
        else ""
    )

    avatar_html = (
        f'<div class="closing-avatar">'
        f'<img src="{html.escape(avatar, quote=True)}" alt="{name}" />'
        f"</div>"
        if avatar
        else ""
    )

    if language == LANGUAGE_EN:
        cta_text = "Follow for more content like this"
    else:
        cta_text = "Siga para mais conteúdo como esse"

    return f"""\
  <div class="slide-content slide-closing">
    <div class="slide-number">0{slide["number"]} / {total_slides:02d}</div>
    {avatar_html}
    <div class="closing-name">{name}</div>
    {handle_html}
    <div class="closing-cta">{cta_text}</div>
  </div>"""
