"""Full HTML carousel template with Neon Shell v2.0 inline CSS."""

import html as html_module
from dataclasses import dataclass

from rag_backend.application.services.carousel.types import SlideDict
from rag_backend.application.services.carousel_template.neon_styles import (
    get_neon_shell_css,
)
from rag_backend.application.services.carousel_template.slides import (
    _render_content_slide,
    _render_cta_slide,
    _render_intro_slide,
    _render_summary_slide,
)
from rag_backend.domain.constants import (
    SLIDE_TYPE_CTA,
    SLIDE_TYPE_INTRO,
    SLIDE_TYPE_SUMMARY,
)
from rag_backend.domain.models import CarouselProject

_FONTS_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900'
    '&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">'
)


def _build_watermark_html(project: CarouselProject) -> str:
    """Return creator watermark HTML if creator metadata is present."""
    name = project.creator_name
    if not name:
        return ""
    handle = project.creator_handle or ""
    avatar = project.creator_avatar_url or ""
    handle_text = f"@{handle}" if handle else ""
    esc = html_module.escape
    avatar_html = (
        f'<div class="creator-watermark-avatar">'
        f'<img src="{esc(avatar, quote=True)}" alt="{esc(name, quote=True)}" />'
        f"</div>"
        if avatar
        else ""
    )
    return (
        f'<div class="creator-watermark">'
        f"{avatar_html}"
        f'<div class="creator-watermark-text">'
        f'<span class="creator-watermark-name">{esc(name, quote=True)}</span>'
        f'<span class="creator-watermark-handle">{esc(handle_text, quote=True)}</span>'
        f"</div></div>"
    )


def _build_slide_counter(total: int, current: int) -> str:
    """Build slide counter dot navigation matching reference."""
    dots = ""
    for i in range(1, total + 1):
        if i < current:
            cls = "counter-dot past"
        elif i == current:
            cls = "counter-dot active"
        else:
            cls = "counter-dot"
        dots += f'<span class="{cls}"></span>'
    return (
        f'<div class="slide-counter">'
        f'<div class="counter-dots">{dots}</div>'
        f'<span class="counter-label">{current}/{total}</span>'
        f"</div>"
    )


def _build_action_bar() -> str:
    """Build Instagram-style action bar with inline SVGs matching reference."""
    heart = (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/>'
        "</svg>"
    )
    comment = (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'
        "</svg>"
    )
    share = (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/>'
        '<polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/>'
        "</svg>"
    )
    save = (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>'
        "</svg>"
    )
    return (
        f'<div class="action-bar">'
        f'<button class="action-btn" aria-label="Curtir">{heart}</button>'
        f'<button class="action-btn" aria-label="Comentar">{comment}</button>'
        f'<button class="action-btn" aria-label="Compartilhar">{share}</button>'
        f'<button class="action-btn action-save" aria-label="Salvar">{save}</button>'
        f"</div>"
    )


def _build_caption_html(project: CarouselProject) -> str:
    """Build caption HTML if caption is present."""
    caption = project.caption
    if not caption:
        return ""
    esc = html_module.escape
    hashtags = ""
    # Extract hashtags from caption if present
    words = caption.split()
    hashtag_words = [w for w in words if w.startswith("#")]
    if hashtag_words:
        hashtags = f'<div class="caption-hashtags">{" ".join(hashtag_words)}</div>'
    return (
        f'<div class="caption">'
        f"<strong>{esc(project.creator_name or 'pedromarins.ai', quote=True)}</strong> "
        f"{esc(caption, quote=True)}{hashtags}"
        f"</div>"
    )


@dataclass(frozen=True)
class SlideWrapContext:
    """Input bundle for wrapping a single slide."""

    inner_html: str
    slide_num: int
    total_slides: int
    watermark_html: str
    include_action_bar: bool = False
    caption_html: str = ""


def _wrap_slide(ctx: SlideWrapContext) -> str:
    """Wrap slide content in Neon Shell v2.0 structure."""
    counter = _build_slide_counter(ctx.total_slides, ctx.slide_num)
    action_bar = _build_action_bar() if ctx.include_action_bar else ""
    return (
        f'<div class="ig-post">'
        f'<div class="ig-slide">'
        f'<div class="ig-slide-inner">'
        f"{ctx.inner_html}"
        f"{ctx.watermark_html}"
        f"</div>"
        f"{counter}"
        f"{action_bar}"
        f"{ctx.caption_html}"
        f"</div></div>"
    )


def build_carousel_html(
    project: CarouselProject,
    slides: list[SlideDict],
    theme: dict[str, str],
    design_overrides: str | None = None,
    language: str | None = None,
) -> str:
    """Build full Neon Shell v2.0 HTML carousel."""
    lang = language or project.language
    total_slides = len(slides)
    watermark_html = _build_watermark_html(project)
    caption_html = _build_caption_html(project)

    slides_html = ""
    for slide in slides:
        slide_type = slide["type"]
        # Include action bar + caption on first and last slides only
        is_first_or_last = slide["number"] in {"1", str(total_slides)}
        if slide_type == SLIDE_TYPE_INTRO:
            inner = _render_intro_slide(slide, project, theme)
        elif slide_type == SLIDE_TYPE_SUMMARY:
            inner = _render_summary_slide(slide, theme, total_slides)
        elif slide_type == SLIDE_TYPE_CTA:
            inner = _render_cta_slide(slide, theme, lang, total_slides)
        else:
            inner = _render_content_slide(slide, theme, total_slides)
        slides_html += _wrap_slide(
            SlideWrapContext(
                inner_html=inner,
                slide_num=int(slide["number"]),
                total_slides=total_slides,
                watermark_html=watermark_html,
                include_action_bar=is_first_or_last,
                caption_html=caption_html if is_first_or_last else "",
            ),
        )

    if design_overrides:
        stripped = design_overrides.strip()
        override_block = f"\n  /* design overrides */\n  {stripped}\n"
    else:
        override_block = ""

    css = get_neon_shell_css(theme)

    esc = html_module.escape
    title_text = esc(project.title or project.topic, quote=True)
    slide_count_text = esc(f"{total_slides} slides", quote=True)
    lang_attr = esc(lang, quote=True)
    niche_text = esc(project.niche, quote=True)

    return f"""<!DOCTYPE html>
<html class="dark" lang="{lang_attr}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_text} - Instagram Carousel</title>
{_FONTS_LINK}
<style>
{css}
{override_block}
</style>
</head>
<body>
<div class="grid-bg" aria-hidden="true">
  <div class="grid-bg-inner"></div>
</div>
<div class="page-header">
  <h1>{title_text}</h1>
  <div class="sub">{niche_text} &middot; {slide_count_text}</div>
</div>
<div class="feed">
{slides_html}
</div>
</body>
</html>"""
