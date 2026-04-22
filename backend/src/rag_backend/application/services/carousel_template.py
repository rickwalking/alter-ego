"""Carousel HTML template generation and prompt building."""

import html
import re
from typing import Any

from rag_backend.domain.constants import SLIDE_TYPE_CONTENT, SLIDE_TYPE_INTRO
from rag_backend.domain.models import CarouselProject, DesignTokens

_EM_DASH_RE = re.compile(r"\s*[—–]+\s*")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_CODE_RE = re.compile(r"`([^`\n]+?)`")


def _render_inline(text: str) -> str:
    """Render inline carousel body text into safe HTML.

    - Escapes HTML first so content can't break the template.
    - Collapses em/en dashes (—, –) into a period + space because those
      dashes are a well-known AI-writing tell. The original skill bans
      them outright and the LLM still slips them in, so we strip
      defensively on the render side as a safety net.
    - Turns Markdown-style **bold** into <strong> (white inside body,
      accent color inside headings — see CSS).
    - Turns Markdown-style `code` into <span class="code-tag">
      pills for technical tokens (package names, versions, file
      extensions, commands) rendered monospace in the primary color.
    """
    escaped = html.escape(text, quote=False)
    without_dashes = _EM_DASH_RE.sub(". ", escaped)
    with_code = _CODE_RE.sub(r'<span class="code-tag">\1</span>', without_dashes)
    return _BOLD_RE.sub(r"<strong>\1</strong>", with_code)


def _feature_items(slide: dict[str, Any]) -> list[dict[str, str]] | None:
    """Return the list of feature/checklist items for this slide, if any.

    The content LLM may return a `features` array on closing/content slides.
    Each item has `icon` (emoji), `title`, `body`. If no valid array is
    present, returns None so the caller falls back to paragraph rendering.
    """
    features = slide.get("features")
    if not isinstance(features, list) or not features:
        return None
    items: list[dict[str, str]] = []
    for entry in features:
        if not isinstance(entry, dict):
            continue
        title = entry.get("title") or ""
        body = entry.get("body") or ""
        if not title and not body:
            continue
        items.append(
            {
                "icon": str(entry.get("icon") or "✅"),
                "title": str(title),
                "body": str(body),
            }
        )
    return items or None


def _stat_items(slide: dict[str, Any]) -> list[dict[str, str]] | None:
    """Return stat-card items for this slide, if any.

    The content LLM may return a `stats` array on content slides with
    `{value, label, detail?}`. Used to render the big-number 3-column
    grid seen on benchmark/metric slides in the reference carousels.
    """
    stats = slide.get("stats")
    if not isinstance(stats, list) or not stats:
        return None
    items: list[dict[str, str]] = []
    for entry in stats:
        if not isinstance(entry, dict):
            continue
        value = str(entry.get("value") or "").strip()
        label = str(entry.get("label") or "").strip()
        if not value:
            continue
        items.append(
            {
                "value": value,
                "label": label,
                "detail": str(entry.get("detail") or ""),
            }
        )
    return items or None


def _insight_quote(slide: dict[str, Any]) -> dict[str, str] | None:
    """Return the insight-card payload for this slide, if any.

    Shape: `{quote, attribution}`. Renders as an italic quote with a
    left-border accent and attribution underneath.
    """
    raw = slide.get("insight")
    if not isinstance(raw, dict):
        return None
    quote = str(raw.get("quote") or "").strip()
    if not quote:
        return None
    return {"quote": quote, "attribution": str(raw.get("attribution") or "").strip()}


def _render_stat_row(items: list[dict[str, str]]) -> str:
    """Render a 3-column grid of stat cards."""
    cards = []
    for item in items:
        detail_html = (
            f'<div class="stat-detail">{_render_inline(item["detail"])}</div>'
            if item.get("detail")
            else ""
        )
        cards.append(
            '<div class="stat-card">'
            f'<div class="stat-number">{_render_inline(item["value"])}</div>'
            f'<div class="stat-label">{_render_inline(item["label"])}</div>'
            f"{detail_html}"
            "</div>"
        )
    return '<div class="stat-row">' + "".join(cards) + "</div>"


def _render_feature_grid(items: list[dict[str, str]], *, columns: int = 1) -> str:
    """Render a 1- or 2-column grid of feature cards."""
    cls = "feature-grid cols-2" if columns == 2 else "feature-grid"
    cards = []
    for item in items:
        cards.append(
            '<div class="feature-item">'
            f'<div class="feature-icon">{html.escape(item["icon"], quote=False)}</div>'
            '<div class="feature-text">'
            f'<div class="feature-title">{_render_inline(item["title"])}</div>'
            f'<div class="feature-body">{_render_inline(item["body"])}</div>'
            "</div></div>"
        )
    return f'<div class="{cls}">' + "".join(cards) + "</div>"


def _render_insight_card(insight: dict[str, str]) -> str:
    """Render a quote with attribution as an accent-bordered card."""
    quote_html = _render_inline(f'"{insight["quote"]}"')
    if insight.get("attribution"):
        quote_html += (
            f'<span class="insight-attribution">{_render_inline(insight["attribution"])}</span>'
        )
    return f'<div class="insight-card">{quote_html}</div>'


THEME_PALETTES: dict[str, dict[str, str]] = {
    "cybersecurity": {
        "primary": "#ef4444",
        "accent": "#00d4ff",
        "background": "#0a0e17",
    },
    "ai_competition": {
        "primary": "#3b82f6",
        "accent": "#f59e0b",
        "background": "#0a0e17",
    },
    "developer_skills": {
        "primary": "#0ac5a8",
        "accent": "#8b5cf6",
        "background": "#080c12",
    },
    "source_code": {
        "primary": "#a855f7",
        "accent": "#f97316",
        "background": "#0c0a14",
    },
    "social_engineering": {
        "primary": "#f59e0b",
        "accent": "#ef4444",
        "background": "#0a0c14",
    },
}


class CarouselTemplateBuilder:
    """Builds HTML carousel templates and LLM prompts."""

    @staticmethod
    def build_title_prompt(project: CarouselProject, research_context: str) -> str:
        """Build prompt for title optimization."""
        return (
            f"Optimize this carousel title for maximum scroll-stop power.\n\n"
            f"Topic: {project.topic}\n"
            f"Audience: {project.audience}\n"
            f"Niche: {project.niche}\n\n"
            f"Research context:\n{research_context}\n\n"
            f"Return ONLY a JSON object with keys: title, subtitle\n"
            f"Title should be max 60 chars, provocative and specific.\n"
        )

    @staticmethod
    def build_content_prompt(project: CarouselProject, research_context: str) -> str:
        """Build prompt for bilingual content synthesis."""
        language_name = (
            "Brazilian Portuguese (informal but professional)"
            if project.language == "pt-BR"
            else "English (professional, direct)"
        )
        return (
            f"Create a 6-slide Instagram carousel and a blog post in TWO languages.\n\n"
            f"Topic: {project.topic}\n"
            f"Title: {project.title}\n"
            f"Subtitle: {project.subtitle}\n"
            f"Audience: {project.audience}\n\n"
            f"Research context:\n{research_context}\n\n"
            f"Slide structure:\n"
            f"1. Intro: hook + hero image\n"
            f"2-4. Content: deep information with stats/quotes\n"
            f"5. Closing: actionable takeaways AS A CHECKLIST\n"
            f"6. CTA: save + share\n\n"
            f"Return ONLY a JSON object with keys:\n"
            f"- slides: array of pt-BR slides\n"
            f"    {{number, type, heading, body, image_prompt,\n"
            f"     features?, stats?, insight?}}\n"
            f"- slides_en: array of EN slides MIRRORING `slides` exactly.\n"
            f"    Same `number` ordering, same `type` per slide. Translate\n"
            f"    `heading`, `body`, and any `features`/`stats`/`insight`\n"
            f"    text fields (title, body, label, detail, quote,\n"
            f"    attribution). Icons + stat numbers stay identical.\n"
            f"    `image_prompt` is omitted — the image is shared.\n"
            f"- blog_pt: full blog post in pt-BR markdown\n"
            f"- blog_en: full blog post in English markdown\n"
            f"- title_pt, title_en, subtitle_pt, subtitle_en\n\n"
            f"Per-slide body format:\n"
            f"- Intro (slide 1): 'body' is a 2-3 sentence subtitle hook. No\n"
            f"  bullet points, no markdown, no features array.\n"
            f"- Content (slides 2-4): 'body' is a dense paragraph (max 4\n"
            f"  sentences). Use **word** for inline emphasis on key terms,\n"
            f"  numbers, and tool names. Do NOT invent your own bullet\n"
            f"  characters; use the structured fields below instead.\n"
            f"  Optional structured extras (use whichever fit the slide):\n"
            f"    * `stats`: array of 3 cards {{value, label, detail?}} for\n"
            f"      benchmark slides, metrics, growth numbers. `value` is\n"
            f"      the big number ('80.2%', '+185%', '2150'). `label` is\n"
            f"      the metric name. Optional `detail` is a small baseline\n"
            f"      comparison like '(era 20.8%)' or '(vs Claude 4.6 53%)'.\n"
            f"      Pick 3 stats max; any fewer and the grid looks sparse.\n"
            f"    * `features`: array of 2-4 items {{icon, title, body}} for\n"
            f"      slides that naturally list things (architecture\n"
            f"      components, sub-products, pillars). Each item renders\n"
            f"      as its own boxed card with the emoji icon, the title\n"
            f"      in white, and the body (backticks + bold allowed).\n"
            f"    * `insight`: {{quote, attribution}} for a single pullquote\n"
            f"      from a primary source (tweet, blog post, interview).\n"
            f"      Renders as an italic card with accent-colored left\n"
            f"      border. Use at most ONE per slide and only on slides\n"
            f"      where an external voice strengthens the point.\n"
            f"  Slides 2-4 should average 1 structured extra each\n"
            f"  (benchmarks slide → stats; architecture slide → features;\n"
            f"  reaction slide → insight quote). Do NOT stack all three\n"
            f"  on the same slide.\n"
            f"- Closing (slide 5): 'body' is a single intro sentence AND the\n"
            f"  actionable takeaways MUST be returned as a `features` array of\n"
            f"  EXACTLY 3 or 4 items (never more — the grid overflows), each\n"
            f"  {{icon, title, body}}:\n"
            f"    - icon: ONE emoji relevant to the item (📝 🏗️ ⚙️ 🧪 🗣️ 🚀 🔒 🧠)\n"
            f"    - title: the action name, 2-5 words\n"
            f"    - body: 1-2 sentences explaining how/why, with **bold** on\n"
            f"      the key tool or concept\n"
            f"  Do NOT cram actions into a single prose paragraph.\n"
            f"- CTA (slide 6): 'body' is 2-3 punchy sentences. No bullets.\n"
            f"\n"
            f"Forbidden characters in ALL text (title, subtitle, headings,\n"
            f"bodies, features, blog): em dash (—) and en dash (–). These\n"
            f"are the #1 AI-writing tell. Use periods, commas, colons, or\n"
            f"parentheses instead. This ban applies to both pt-BR and EN.\n"
            f"\n"
            f"Inline emphasis, two flavors:\n"
            f"- **bold** (double asterisks) for prose emphasis: key\n"
            f"  phrases, numbers, stats, company/person names. Renders\n"
            f"  as <strong> (white bold inside body, accent color inside\n"
            f"  headings).\n"
            f"- `code` (backticks) for TECHNICAL TOKENS: package names\n"
            f"  (`axios`, `moonshotai/Kimi-K2.6`), versions (`2.1.88`,\n"
            f"  `v4.9`), file patterns (`*.map`, `.npmignore`), commands\n"
            f"  (`npm publish`, `kimi-code`), config keys\n"
            f"  (`temperature=1.0`, `top_p=0.9`), or env vars\n"
            f"  (`ANTHROPIC_API_KEY`). Renders as a monospace pill in the\n"
            f"  primary palette color. Use this instead of **bold** when\n"
            f"  the term is a literal code/config token.\n"
            f"- Rule of thumb: if a reader would copy/paste it into a\n"
            f"  terminal or config file, wrap it in backticks. Otherwise\n"
            f"  use **bold**.\n"
            f"\n"
            f"EVERY slide heading (title) must mark 1-2 key words with **...**\n"
            f"so the renderer paints them in the palette accent color. Pick\n"
            f"the word that carries the emotional punch or the specific\n"
            f"subject. Examples:\n"
            f"  - 'Código do Claude Code **vazou**. O que descobrimos?'\n"
            f"  - 'As **features escondidas** que ninguém deveria ver'\n"
            f"  - 'O **impacto** e a reação da comunidade'\n"
            f"  - 'O que isso **significa** pra devs'\n"
            f"Never highlight a whole heading; 1-2 words max. The rest stays\n"
            f"white so the highlight does its job.\n"
            f"\n"
            f"Other rules:\n"
            f"- pt-BR version: {language_name}, engaging\n"
            f"- EN version: professional, direct, same depth and structure\n"
            f"- Each slide must have complete explanatory content\n"
            f"- Blog post should expand on carousel content\n"
            f"\n"
            f"image_prompt rules (CRITICAL — the system wraps it with style\n"
            f"directives, so describe the SCENE ONLY):\n"
            f"- 1-2 sentences describing a concrete cyberpunk/sci-fi tech\n"
            f"  scene. Example: 'two hooded figures at glowing terminals\n"
            f"  watching a package registry map pulse with red alerts'.\n"
            f"- DO NOT specify style, colors, lighting, panel layouts, or\n"
            f"  ratio — those are applied by the system.\n"
            f"- DO NOT request any text, labels, speech bubbles, signs,\n"
            f"  or words to appear in the image.\n"
            f"- DO NOT use metaphorical/cultural settings (dojos, sensei,\n"
            f"  crossroads, books). Use tech scenes only.\n"
            f"- Elements to favor: monitors, terminals, code streams,\n"
            f"  neon cityscapes, robots, circuit boards, holograms,\n"
            f"  servers, data pipelines.\n"
        )

    @staticmethod
    def generate_design_tokens(project: CarouselProject) -> DesignTokens:
        """Generate complete design tokens for a blog post."""
        from rag_backend.domain.constants import CAROUSEL_THEMES as PALETTES

        theme = PALETTES.get(project.theme.value, PALETTES["ai_competition"])
        primary = theme["primary"]
        accent = theme["accent"]
        bg = theme["background"]
        swipe_text = "Deslize \u2192" if project.language == "pt-BR" else "Swipe \u2192"

        return DesignTokens(
            colors={
                "primary": primary,
                "accent": accent,
                "bg": bg,
                "text": "#ffffff",
                "text_muted": "rgba(255,255,255,0.63)",
                "text_dim": "rgba(255,255,255,0.48)",
                "border": f"{primary}33",
                "glow": f"{primary}0D",
            },
            typography={
                "font_family_heading": "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
                "font_family_body": "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
                "font_family_badge": "'Courier New', monospace",
            },
            images={
                # `hero` + `slides` reference the RAW OpenAI/Gemini hero
                # images (no text overlay) — used by the blog page so the
                # inline figures show the photographic source, not the
                # composed slide. `rendered_slides_*` reference the FINAL
                # slides with text overlay (output of phase 6) — used by
                # the publish carousel viewer.
                "hero": f"/api/carousels/{project.id}/images/slide_1",
                "slides": [f"/api/carousels/{project.id}/images/slide_{i}" for i in range(1, 5)],
                "rendered_slides_pt": [
                    f"/api/carousels/{project.id}/slide-images/pt/slide_{i}" for i in range(1, 5)
                ],
                "rendered_slides_en": [
                    f"/api/carousels/{project.id}/slide-images/en/slide_{i}" for i in range(1, 5)
                ],
            },
            layout={
                "badge_label": project.niche,
                "swipe_text": swipe_text,
                "progress_segments": 6,
            },
        )

    @staticmethod
    def build_caption_prompt(
        project: CarouselProject, slide_headings: list[tuple[int, str]]
    ) -> str:
        """Build prompt for Instagram caption generation."""
        slide_summaries = "\n".join(f"Slide {num}: {heading}" for num, heading in slide_headings)
        return (
            f"Generate an Instagram caption for this carousel.\n\n"
            f"Title: {project.title}\n"
            f"Slides:\n{slide_summaries}\n\n"
            f"Structure:\n"
            f"1. Hook (1-2 lines with emoji)\n"
            f"2. Value promise\n"
            f"3. Comment question\n"
            f"4. Double CTA (save + share)\n"
            f"5. 12-18 hashtags mixing Portuguese and English\n\n"
            f"Style: Informal Brazilian Portuguese, engaging, use emojis.\n"
        )

    @staticmethod
    def build_carousel_html(
        project: CarouselProject,
        slides: list[dict[str, Any]],
        theme: dict[str, str],
    ) -> str:
        """Build complete HTML carousel with inline CSS."""
        primary = theme["primary"]
        accent = theme["accent"]
        bg = theme["background"]

        slides_html = ""
        for slide in slides:
            slide_type = slide["type"]
            if slide_type == SLIDE_TYPE_INTRO:
                slides_html += CarouselTemplateBuilder._render_intro_slide(slide, project, theme)
            elif slide_type == "cta":
                slides_html += CarouselTemplateBuilder._render_cta_slide(slide, theme)
            else:
                slides_html += CarouselTemplateBuilder._render_content_slide(slide, theme)

        return f"""<!DOCTYPE html>
<html lang="{project.language}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  :root {{
    --primary: {primary};
    --accent: {accent};
    --bg: {bg};
    --text: #ffffff;
    --text-60: rgba(255,255,255,0.63);
    --text-48: rgba(255,255,255,0.48);
    --text-45: rgba(255,255,255,0.45);
    --text-06: rgba(255,255,255,0.06);
  }}
  body {{ background: #000; font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }}
  .slide {{
    width: 1080px; height: 1350px; background: var(--bg);
    position: relative; overflow: hidden; margin: 0 auto 20px;
  }}
  .bg-glow {{ position: absolute; inset: 0; pointer-events: none; }}
  .bg-glow::before {{
    content: ''; position: absolute; width: 600px; height: 600px;
    border-radius: 50%; top: -100px; right: -150px;
    background: radial-gradient(circle, {primary}0D 0%, transparent 70%);
  }}
  .bg-glow::after {{
    content: ''; position: absolute; width: 500px; height: 500px;
    border-radius: 50%; bottom: -100px; left: -100px;
    background: radial-gradient(circle, {accent}0D 0%, transparent 70%);
  }}
  .s1-content {{
    position: relative; z-index: 1; display: flex; flex-direction: column;
    height: 100%; padding: 70px 72px 60px;
  }}
  .s1-main {{ flex: 1; }}
  .s1-badge {{
    display: inline-flex; align-self: flex-start; padding: 8px 18px;
    border: 1px solid {primary}4D; border-radius: 6px;
    background: {primary}14; font-size: 16px; font-weight: 700;
    font-family: 'Courier New', monospace; color: {primary};
    text-transform: uppercase; letter-spacing: 3px; margin-bottom: 32px;
  }}
  .s1-hero-img {{
    width: 100%; height: 380px; border-radius: 20px; overflow: hidden;
    border: 1px solid {primary}33; margin-bottom: 40px; position: relative;
  }}
  .s1-hero-img img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .s1-hero-img::after {{
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(to bottom, transparent 40%, var(--bg) 100%);
  }}
  .s1-title {{
    font-size: 52px; font-weight: 800; color: var(--text);
    line-height: 1.15; margin-bottom: 20px;
  }}
  .s1-title strong {{ color: {accent}; font-weight: 800; }}
  .s1-subtitle {{
    font-size: 28px; font-weight: 400; color: var(--text-48); line-height: 1.5;
  }}
  .s1-subtitle strong {{ color: var(--text); font-weight: 600; }}
  .content-slide {{
    padding: 70px 72px 60px; display: flex; flex-direction: column;
  }}
  .slide-num {{
    font-size: 16px; font-weight: 700; font-family: 'Courier New', monospace;
    color: {primary}; text-transform: uppercase; letter-spacing: 3px; margin-bottom: 16px;
  }}
  .slide-heading {{
    font-size: 50px; font-weight: 800; color: var(--text);
    line-height: 1.15; margin-bottom: 28px;
  }}
  .slide-heading strong {{ color: {accent}; font-weight: 800; }}
  .hero-img {{
    width: 100%; height: 310px; border-radius: 18px; overflow: hidden;
    border: 1px solid {primary}33; margin-bottom: 28px;
  }}
  .hero-img img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .slide-body {{ flex: 1; }}
  .body-p {{
    font-size: 30px; font-weight: 400; color: var(--text-60);
    line-height: 1.5; margin-bottom: 20px;
  }}
  .body-p strong {{ color: var(--text); font-weight: 700; }}
  .code-tag {{
    display: inline-block;
    padding: 2px 10px;
    margin: 0 2px;
    border-radius: 6px;
    background: {primary}1F;
    color: {primary};
    font-family: 'Courier New', monospace;
    font-size: 0.85em;
    font-weight: 600;
    letter-spacing: 0.3px;
  }}
  .feature-grid {{
    display: flex; flex-direction: column; gap: 16px; margin-top: 8px;
  }}
  .feature-item {{
    display: flex; gap: 20px; align-items: flex-start;
    padding: 22px 24px; border-radius: 16px;
    background: rgba(255,255,255,0.02);
    border: 1px solid {primary}26;
  }}
  .feature-icon {{ font-size: 34px; line-height: 1; flex-shrink: 0; }}
  .feature-text {{ flex: 1; }}
  .feature-title {{
    font-size: 28px; font-weight: 700; color: var(--text);
    margin-bottom: 6px; line-height: 1.25;
  }}
  .feature-body {{
    font-size: 24px; color: var(--text-60); line-height: 1.45;
  }}
  .feature-body strong {{ color: var(--text); font-weight: 700; }}
  .feature-grid.cols-2 {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
  }}
  .stat-row {{
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 16px; margin: 20px 0;
  }}
  .stat-card {{
    background: rgba(255,255,255,0.03);
    border: 1px solid {primary}26; border-radius: 16px;
    padding: 24px 18px; text-align: center;
  }}
  .stat-number {{
    font-size: 40px; font-weight: 900; color: {accent};
    line-height: 1; margin-bottom: 8px;
  }}
  .stat-label {{
    font-size: 20px; color: var(--text-60);
    line-height: 1.3;
  }}
  .stat-detail {{
    font-size: 18px; color: var(--text-45);
    margin-top: 4px; line-height: 1.3;
  }}
  .insight-card {{
    border-left: 3px solid {primary}; padding: 10px 24px;
    margin: 20px 0; font-size: 26px; font-style: italic;
    color: var(--text-60); line-height: 1.45;
  }}
  .insight-card strong {{ color: var(--text); font-weight: 600; font-style: italic; }}
  .insight-attribution {{
    display: block; font-size: 20px; font-style: normal;
    color: var(--text-45); margin-top: 8px;
  }}
  .progress {{
    position: absolute; bottom: 40px; left: 72px; right: 72px;
    display: flex; gap: 8px;
  }}
  .progress .bar {{
    flex: 1; height: 4px; border-radius: 2px; background: var(--text-06);
  }}
  .progress .bar.active {{ background: {primary}; }}
  .cta-slide {{
    display: flex; align-items: center; justify-content: center;
    text-align: center; padding: 70px 72px;
  }}
  .cta-icon {{ font-size: 64px; margin-bottom: 32px; }}
  .cta-title {{
    font-size: 52px; font-weight: 800; color: var(--text); margin-bottom: 24px;
  }}
  .cta-title strong {{ color: {accent}; font-weight: 800; }}
  .cta-body {{
    font-size: 31px; color: var(--text-48); margin-bottom: 48px; line-height: 1.5;
  }}
  .cta-row {{ display: flex; gap: 24px; justify-content: center; }}
  .cta-btn {{
    padding: 18px 36px; border-radius: 12px; font-size: 24px; font-weight: 600;
  }}
  .cta-btn.primary {{ background: {primary}; color: #fff; }}
  .cta-btn.secondary {{ border: 1px solid {primary}4D; color: {primary}; }}
</style>
</head>
<body>
{slides_html}
</body>
</html>"""

    @staticmethod
    def _render_intro_slide(
        slide: dict[str, Any], project: CarouselProject, theme: dict[str, str]
    ) -> str:
        """Render intro slide HTML."""
        primary = theme["primary"]
        heading = _render_inline(str(slide["heading"]))
        subtitle = _render_inline(str(slide["body"]))
        badge = html.escape(project.niche, quote=False)
        audience = html.escape(project.audience, quote=False)
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
      </div>
      <div class="s1-footer" style="display:flex;justify-content:space-between;
        padding-top:24px;border-top:1px solid rgba(255,255,255,0.06);">
        <span style="font-size:18px;color:rgba(255,255,255,0.45);">{audience}</span>
        <span style="font-size:18px;color:{primary};font-weight:600;">Deslize &#8594;</span>
      </div>
    </div>
  </div>"""

    @staticmethod
    def _render_content_slide(slide: dict[str, Any], theme: dict[str, str]) -> str:
        """Render content slide HTML."""
        total_slides = 6
        active_bar = int(slide["number"])
        bars = ""
        for i in range(1, total_slides + 1):
            active_class = "active" if i <= active_bar else ""
            bars += f'<div class="bar {active_class}"></div>'

        image_html = ""
        if slide["type"] == SLIDE_TYPE_CONTENT:
            image_html = f"""
      <div class="hero-img">
        <img src="images/slide_{slide["number"]}.jpg" alt="{_render_inline(str(slide["heading"]))}" />
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
            columns = 2 if len(features) >= 4 and slide["type"] != "closing" else 1
            body_parts.append(_render_feature_grid(features, columns=columns))

        insight = _insight_quote(slide)
        if insight is not None:
            body_parts.append(_render_insight_card(insight))

        body_html = "".join(body_parts) or (f'<p class="body-p">{_render_inline(raw_body)}</p>')

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

    @staticmethod
    def _render_cta_slide(slide: dict[str, Any], theme: dict[str, str]) -> str:
        """Render CTA slide HTML."""
        heading = _render_inline(str(slide["heading"]))
        body = _render_inline(str(slide["body"]))
        return f"""
  <div class="slide cta-slide">
    <div class="bg-glow"></div>
    <div class="cta-content" style="max-width:900px;">
      <div class="cta-icon">&#128640;</div>
      <h2 class="cta-title">{heading}</h2>
      <p class="cta-body">{body}</p>
      <div class="cta-row">
        <div class="cta-btn primary">&#128190; Salve este post</div>
        <div class="cta-btn secondary">&#128260; Compartilhe</div>
      </div>
    </div>
  </div>"""
