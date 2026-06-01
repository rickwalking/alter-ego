"""Individual slide renderers for carousel HTML matching Neon Shell v2.0 reference."""

import html

from rag_backend.application.services.carousel.types import (
    MAX_FEATURE_ITEMS,
    SlideDict,
)
from rag_backend.application.services.carousel_template.helpers import (
    _feature_items,
    _insight_quote,
    _render_feature_grid,
    _render_inline,
    _render_insight_card,
    _render_stat_row,
    _stat_items,
)
from rag_backend.domain.constants import (
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CONTENT,
    SWIPE_TEXT_PT,
)
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
    slide: SlideDict, _theme: dict[str, str], total_slides: int = 6
) -> str:
    """Render summary slide matching reference structure."""
    summary_points = slide.get("summary_points")
    points_html = ""
    if isinstance(summary_points, list) and summary_points:
        cards: list[str] = []
        for item in summary_points:
            if not isinstance(item, dict):
                continue
            icon = html.escape(str(item.get("icon") or "🎯"), quote=True)
            title = _render_inline(str(item.get("title") or ""))
            body = _render_inline(str(item.get("body") or ""))
            cards.append(
                '<div class="summary-item">'
                f'<div class="summary-icon">{icon}</div>'
                '<div class="summary-text">'
                f'<div class="summary-title">{title}</div>'
                f'<div class="summary-body">{body}</div>'
                "</div></div>"
            )
        points_html = '<div class="summary-grid">' + "".join(cards) + "</div>"

    heading = _render_inline(str(slide["heading"]))
    subtitle_raw = str(slide.get("body") or "").strip()
    subtitle_html = (
        f'<p class="body-p">{_render_inline(subtitle_raw)}</p>' if subtitle_raw else ""
    )
    return f"""\
  <div class="bg-glow"></div>
  <div class="slide-content">
    <div class="slide-number">0{slide["number"]} / {total_slides:02d}</div>
    <h2 class="slide-heading">{heading}</h2>
    {subtitle_html}
    <div class="slide-body">
      {points_html}
    </div>
  </div>"""


def _render_content_slide(
    slide: SlideDict, _theme: dict[str, str], total_slides: int = 6
) -> str:
    """Render content slide matching reference structure."""
    image_html = ""
    if slide["type"] == SLIDE_TYPE_CONTENT:
        heading_esc = _render_inline(str(slide["heading"]))
        image_html = f"""\
      <div class="hero-img hero-img-md">
        <img src="images/slide_{slide["number"]}.jpg" alt="{heading_esc}" />
      </div>"""

    body_parts: list[str] = []
    raw_body = str(slide.get("body") or "").strip()
    if raw_body:
        body_parts.append(f'<p class="body-p">{_render_inline(raw_body)}</p>')

    stats = _stat_items(slide)
    if stats is not None:
        body_parts.append(_render_stat_row(stats))

    features = _feature_items(slide)
    if features is not None:
        columns = (
            2
            if len(features) >= MAX_FEATURE_ITEMS
            and slide["type"] != SLIDE_TYPE_CLOSING
            else 1
        )
        body_parts.append(_render_feature_grid(features, columns=columns))

    insight = _insight_quote(slide)
    if insight is not None:
        body_parts.append(_render_insight_card(insight))

    body_html = "".join(body_parts) or (
        f'<p class="body-p">{_render_inline(raw_body)}</p>'
    )

    heading = _render_inline(str(slide["heading"]))
    return f"""\
  <div class="bg-glow"></div>
  <div class="slide-content content-slide">
    <div class="slide-number">0{slide["number"]} / {total_slides:02d}</div>
    <h2 class="slide-heading">{heading}</h2>
    {image_html}
    <div class="slide-body">
      {body_html}
    </div>
  </div>"""


def _render_cta_slide(
    slide: SlideDict,
    _theme: dict[str, str],
    language: str = "pt",
    total_slides: int = 6,
) -> str:
    """Render CTA slide matching reference structure."""
    heading = _render_inline(str(slide["heading"]))
    body = _render_inline(str(slide["body"]))
    from rag_backend.domain.constants import LANGUAGE_EN

    if language == LANGUAGE_EN:
        save_text = "Save this post"
        share_text = "Share"
    else:
        save_text = "Salvar"
        share_text = "Compartilhar"

    return f"""\
  <div class="bg-glow"></div>
  <div class="slide-content slide-cta">
    <div class="slide-number">0{slide["number"]} / {total_slides:02d}</div>
    <div class="cta-icon">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2l4 7-4 4-4-4z"/><path d="M10 13v4l4-2v-2"/><circle cx="12" cy="7" r="1" fill="currentColor" opacity="0.3"/>
      </svg>
    </div>
    <h2 class="cta-title">{heading}</h2>
    <p class="cta-body">{body}</p>
    <div class="cta-row">
      <div class="cta-btn primary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
        </svg>
        {save_text}
      </div>
      <div class="cta-btn secondary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
        </svg>
        {share_text}
      </div>
    </div>
  </div>"""
