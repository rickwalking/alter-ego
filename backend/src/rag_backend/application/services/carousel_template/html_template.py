"""Full HTML carousel template with inline CSS."""

from rag_backend.application.services.carousel.types import SlideDict
from rag_backend.application.services.carousel_template.slides import (
    _render_content_slide,
    _render_cta_slide,
    _render_intro_slide,
    _render_summary_slide,
)
from rag_backend.domain.constants import SLIDE_TYPE_INTRO, SLIDE_TYPE_SUMMARY
from rag_backend.domain.models import CarouselProject


def build_carousel_html(
    project: CarouselProject,
    slides: list[SlideDict],
    theme: dict[str, str],
    design_overrides: str | None = None,
    language: str | None = None,
) -> str:
    primary = theme["primary"]
    accent = theme["accent"]
    bg = theme["background"]
    lang = language or project.language

    slides_html = ""
    for slide in slides:
        slide_type = slide["type"]
        if slide_type == SLIDE_TYPE_INTRO:
            slides_html += _render_intro_slide(slide, project, theme)
        elif slide_type == SLIDE_TYPE_SUMMARY:
            slides_html += _render_summary_slide(slide, theme)
        elif slide_type == "cta":
            slides_html += _render_cta_slide(slide, theme, lang)
        else:
            slides_html += _render_content_slide(slide, theme)

    if design_overrides:
        stripped = design_overrides.strip()
        override_block = f"\n  /* design overrides */\n  {stripped}\n"
    else:
        override_block = ""

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
  }}{override_block}
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
  .tldr-strip {{
    margin-top: 20px;
    padding: 14px 18px;
    border-radius: 10px;
    border-left: 3px solid {accent};
    background: {primary}14;
    font-size: 22px;
    font-weight: 500;
    color: var(--text-60);
    line-height: 1.4;
  }}
  .tldr-strip strong {{ color: var(--text); font-weight: 700; }}
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
  .summary-slide {{
    padding: 70px 72px 60px; display: flex; flex-direction: column;
  }}
  .summary-bg {{
    position: absolute; inset: 0; z-index: 0;
    overflow: hidden;
  }}
  .summary-bg-img {{
    position: absolute; inset: 0; width: 100%; height: 100%;
    object-fit: cover; display: block;
    filter: blur(6px) brightness(1.0);
  }}
  .summary-bg::after {{
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(to bottom, {bg}99 0%, {bg}66 100%);
  }}
  .summary-slide > *:not(.summary-bg):not(.progress) {{ position: relative; z-index: 1; }}
  .summary-subtitle {{
    font-size: 24px; color: var(--text-45); margin-top: -16px;
    margin-bottom: 24px; font-weight: 400;
  }}
  .summary-grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
  }}
  .summary-grid > .summary-item:nth-child(3) {{
    grid-column: 1 / -1;
  }}
  .summary-item {{
    display: flex; gap: 18px; align-items: flex-start;
    padding: 28px 24px; border-radius: 16px;
    background: rgba(8,12,18,0.88);
    border: 1px solid {primary}45;
    border-top: 3px solid {accent};
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
  }}
  .summary-icon {{ font-size: 36px; line-height: 1; flex-shrink: 0; }}
  .summary-text {{ flex: 1; }}
  .summary-title {{
    font-size: 30px; font-weight: 700; color: var(--text);
    margin-bottom: 6px; line-height: 1.25;
  }}
  .summary-body {{
    font-size: 24px; color: var(--text-60); line-height: 1.5;
  }}
  .summary-body strong {{ color: var(--text); font-weight: 700; }}
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
