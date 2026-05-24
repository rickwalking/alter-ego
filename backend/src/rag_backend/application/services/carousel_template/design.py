"""Carousel design tokens and theme palettes."""

from rag_backend.application.services.carousel.types import slide_count_from_config
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


def generate_design_tokens(project: CarouselProject) -> DesignTokens:
    from rag_backend.application.services.carousel.theme_resolver import (
        resolve_theme,
    )

    theme = resolve_theme(project)
    primary = theme["primary"]
    accent = theme["accent"]
    bg = theme["background"]
    slide_count = slide_count_from_config(project.slides_config)
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
            "hero": f"/api/carousels/{project.id}/images/slide_1",
            "slides": [
                f"/api/carousels/{project.id}/images/slide_{i}" for i in range(1, slide_count + 1)
            ],
            "rendered_slides_pt": [
                f"/api/carousels/{project.id}/slide-images/pt/slide_{i}"
                for i in range(1, slide_count + 1)
            ],
            "rendered_slides_en": [
                f"/api/carousels/{project.id}/slide-images/en/slide_{i}"
                for i in range(1, slide_count + 1)
            ],
            "blog_image_map": project.blog_image_map,
        },
        layout={
            "badge_label": project.niche,
            "swipe_text": swipe_text,
            "progress_segments": slide_count,
        },
    )
