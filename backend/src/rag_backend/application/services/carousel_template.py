"""Carousel HTML template generation and prompt building."""

from rag_backend.domain.constants import SLIDE_TYPE_CONTENT, SLIDE_TYPE_INTRO
from rag_backend.domain.models import CarouselProject, DesignTokens

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
            f"5. Closing: actionable takeaways\n"
            f"6. CTA: save + share\n\n"
            f"Return ONLY a JSON object with keys:\n"
            f"- slides: array of {{number, type, heading, body, image_prompt}} in pt-BR\n"
            f"- blog_pt: full blog post in pt-BR markdown\n"
            f"- blog_en: full blog post in English markdown\n"
            f"- title_pt, title_en, subtitle_pt, subtitle_en\n\n"
            f"Rules:\n"
            f"- pt-BR version: {language_name}, engaging\n"
            f"- EN version: professional, direct, same depth and structure\n"
            f"- NEVER use em dashes in either language\n"
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
                # The intro slide's rendered image IS the hero; the pipeline
                # writes it to images/slide_1.jpg. There is no separate
                # "hero" file on disk.
                "hero": f"/api/carousels/{project.id}/images/slide_1",
                "slides": [
                    f"/api/carousels/{project.id}/images/slide_{i}"
                    for i in range(1, 5)
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
        slide_summaries = "\n".join(
            f"Slide {num}: {heading}" for num, heading in slide_headings
        )
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
        slides: list[dict[str, str]],
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
                slides_html += CarouselTemplateBuilder._render_intro_slide(
                    slide, project, theme
                )
            elif slide_type == "cta":
                slides_html += CarouselTemplateBuilder._render_cta_slide(slide, theme)
            else:
                slides_html += CarouselTemplateBuilder._render_content_slide(
                    slide, theme
                )

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
  .s1-subtitle {{
    font-size: 28px; font-weight: 400; color: var(--text-48); line-height: 1.5;
  }}
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
    height: 100%; text-align: center; padding: 70px 72px;
  }}
  .cta-icon {{ font-size: 64px; margin-bottom: 32px; }}
  .cta-title {{
    font-size: 52px; font-weight: 800; color: var(--text); margin-bottom: 24px;
  }}
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
        slide: dict[str, str], project: CarouselProject, theme: dict[str, str]
    ) -> str:
        """Render intro slide HTML."""
        primary = theme["primary"]
        return f"""
  <div class="slide">
    <div class="bg-glow"></div>
    <div class="s1-content">
      <div class="s1-badge">{project.niche}</div>
      <div class="s1-hero-img">
        <img src="images/slide_{slide['number']}.jpg" alt="{slide['heading']}" />
      </div>
      <div class="s1-main">
        <h1 class="s1-title">{slide['heading']}</h1>
        <p class="s1-subtitle">{slide['body']}</p>
      </div>
      <div class="s1-footer" style="display:flex;justify-content:space-between;
        padding-top:24px;border-top:1px solid rgba(255,255,255,0.06);">
        <span style="font-size:18px;color:rgba(255,255,255,0.45);">{project.audience}</span>
        <span style="font-size:18px;color:{primary};font-weight:600;">Deslize &#8594;</span>
      </div>
    </div>
  </div>"""

    @staticmethod
    def _render_content_slide(slide: dict[str, str], theme: dict[str, str]) -> str:
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
        <img src="images/slide_{slide['number']}.jpg" alt="{slide['heading']}" />
      </div>"""

        return f"""
  <div class="slide content-slide">
    <div class="bg-glow"></div>
    <div class="slide-num">0{slide['number']}</div>
    <h2 class="slide-heading">{slide['heading']}</h2>
    {image_html}
    <div class="slide-body">
      <p class="body-p">{slide['body']}</p>
    </div>
    <div class="progress">{bars}</div>
  </div>"""

    @staticmethod
    def _render_cta_slide(slide: dict[str, str], theme: dict[str, str]) -> str:
        """Render CTA slide HTML."""
        return f"""
  <div class="slide cta-slide">
    <div class="bg-glow"></div>
    <div class="cta-content">
      <div class="cta-icon">&#128640;</div>
      <h2 class="cta-title">{slide['heading']}</h2>
      <p class="cta-body">{slide['body']}</p>
      <div class="cta-row">
        <div class="cta-btn primary">&#128190; Salve este post</div>
        <div class="cta-btn secondary">&#128260; Compartilhe</div>
      </div>
    </div>
  </div>"""
