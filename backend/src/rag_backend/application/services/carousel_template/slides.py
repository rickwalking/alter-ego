"""Individual slide renderers for carousel HTML."""

import html

from rag_backend.application.services.carousel.types import (
    MAX_FEATURE_ITEMS,
    MAX_SLIDES,
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
from rag_backend.domain.constants import SLIDE_TYPE_CONTENT
from rag_backend.domain.models import CarouselProject


def _render_intro_slide(
    slide: SlideDict, project: CarouselProject, theme: dict[str, str]
) -> str:
    primary = theme["primary"]
    heading = _render_inline(str(slide["heading"]))
    subtitle = _render_inline(str(slide["body"]))
    badge = html.escape(project.niche, quote=False)
    audience = html.escape(project.audience, quote=False)
    tldr = slide.get("tldr_strip")
    tldr_html = ""
    if tldr:
        tldr_html = f'<div class="tldr-strip">{_render_inline(str(tldr))}</div>'
    return f"""
  <div class="slide">
    <div class="bg-glow"></div>
    <div class="s1-content">
      <div class="s1-badge">{badge}</div>
      <div class="s1-hero-img">
        <img src="images/slide_{slide["number"]}.jpg" alt="{heading}" />
      </div>
      <div class="s1-main">
        <h1 class="s1-title">{heading}</h1>
        <p class="s1-subtitle">{subtitle}</p>
        {tldr_html}
      </div>
      <div class="s1-footer" style="display:flex;justify-content:space-between;
        padding-top:24px;border-top:1px solid rgba(255,255,255,0.06);">
        <span style="font-size:18px;color:rgba(255,255,255,0.45);">{audience}</span>
        <span style="font-size:18px;color:{primary};font-weight:600;">Deslize &#8594;</span>
      </div>
    </div>
  </div>"""


def _render_summary_slide(slide: SlideDict, _theme: dict[str, str]) -> str:
    active_bar = int(slide["number"])
    bars = ""
    for i in range(1, MAX_SLIDES + 1):
        active_class = "active" if i <= active_bar else ""
        bars += f'<div class="bar {active_class}"></div>'

    summary_points = slide.get("summary_points")
    points_html = ""
    if isinstance(summary_points, list) and summary_points:
        cards: list[str] = []
        for item in summary_points:
            if not isinstance(item, dict):
                continue
            icon = html.escape(str(item.get("icon") or "🎯"), quote=False)
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
        f'<p class="summary-subtitle">{_render_inline(subtitle_raw)}</p>'
        if subtitle_raw
        else ""
    )
    return f"""
  <div class="slide summary-slide">
    <div class="summary-bg">
      <img src="images/slide_1.jpg" class="summary-bg-img" alt="" />
    </div>
    <div class="bg-glow"></div>
    <div class="slide-num">0{slide["number"]}</div>
    <h2 class="slide-heading">{heading}</h2>
    {subtitle_html}
    <div class="slide-body">
      {points_html}
    </div>
    <div class="progress">{bars}</div>
  </div>"""


def _render_content_slide(slide: SlideDict, _theme: dict[str, str]) -> str:
    active_bar = int(slide["number"])
    bars = ""
    for i in range(1, MAX_SLIDES + 1):
        active_class = "active" if i <= active_bar else ""
        bars += f'<div class="bar {active_class}"></div>'

    image_html = ""
    if slide["type"] == SLIDE_TYPE_CONTENT:
        heading_esc = _render_inline(str(slide["heading"]))
        image_html = f"""
      <div class="hero-img">
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
            if len(features) >= MAX_FEATURE_ITEMS and slide["type"] != "closing"
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
    return f"""
  <div class="slide content-slide">
    <div class="bg-glow"></div>
    <div class="slide-num">0{slide["number"]}</div>
    <h2 class="slide-heading">{heading}</h2>
    {image_html}
    <div class="slide-body">
      {body_html}
    </div>
    <div class="progress">{bars}</div>
  </div>"""


def _render_cta_slide(
    slide: SlideDict, _theme: dict[str, str], language: str = "pt"
) -> str:
    heading = _render_inline(str(slide["heading"]))
    body = _render_inline(str(slide["body"]))
    if language == "en":
        save_text = "Save this post"
        share_text = "Share"
    else:
        save_text = "Salve este post"
        share_text = "Compartilhe"
    return f"""
  <div class="slide cta-slide">
    <div class="bg-glow"></div>
    <div class="cta-content" style="max-width:900px;">
      <div class="cta-icon">&#128640;</div>
      <h2 class="cta-title">{heading}</h2>
      <p class="cta-body">{body}</p>
      <div class="cta-row">
        <div class="cta-btn primary">&#128190; {save_text}</div>
        <div class="cta-btn secondary">&#128260; {share_text}</div>
      </div>
    </div>
  </div>"""
