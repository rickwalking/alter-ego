"""Unit tests for CarouselTemplateBuilder design tokens and basic HTML."""

import pytest

from rag_backend.application.services.carousel_template import (
    THEME_PALETTES,
    CarouselTemplateBuilder,
)
from rag_backend.domain.models import CarouselProject, CarouselTheme


@pytest.mark.unit
class TestGenerateDesignTokens:
    """Tests for CarouselTemplateBuilder.generate_design_tokens()."""

    def test_generate_design_tokens_ai_competition(self, sample_project):
        """Should generate correct design tokens for ai_competition theme."""
        tokens = CarouselTemplateBuilder.generate_design_tokens(sample_project)

        assert tokens["colors"]["primary"] == "#3b82f6"
        assert tokens["colors"]["accent"] == "#f59e0b"
        assert tokens["colors"]["bg"] == "#0a0e17"
        assert tokens["colors"]["text"] == "#ffffff"
        assert tokens["typography"]["font_family_badge"] == "'Courier New', monospace"
        assert tokens["layout"]["badge_label"] == "AI Education"
        assert tokens["layout"]["progress_segments"] == 6

    def test_generate_design_tokens_cybersecurity(self):
        """Should generate correct design tokens for cybersecurity theme."""
        project = CarouselProject(
            topic="Cyber Attack",
            audience="Security pros",
            niche="Cybersecurity",
            theme=CarouselTheme.CYBERSECURITY,
        )
        tokens = CarouselTemplateBuilder.generate_design_tokens(project)

        assert tokens["colors"]["primary"] == "#ef4444"
        assert tokens["colors"]["accent"] == "#00d4ff"
        assert tokens["colors"]["bg"] == "#0a0e17"

    def test_generate_design_tokens_image_urls(self, sample_project):
        """Should generate image URLs with project ID."""
        tokens = CarouselTemplateBuilder.generate_design_tokens(sample_project)

        assert (
            tokens["images"]["hero"]
            == f"/api/carousels/{sample_project.id}/images/slide_1"
        )
        assert len(tokens["images"]["slides"]) == 6
        assert (
            tokens["images"]["slides"][0]
            == f"/api/carousels/{sample_project.id}/images/slide_1"
        )
        assert "rendered_slides_pt" in tokens["images"]
        assert len(tokens["images"]["rendered_slides_pt"]) == 6
        assert (
            tokens["images"]["rendered_slides_pt"][0]
            == f"/api/carousels/{sample_project.id}/slide-images/pt/slide_1"
        )
        assert "rendered_slides_en" in tokens["images"]
        assert len(tokens["images"]["rendered_slides_en"]) == 6
        assert (
            tokens["images"]["rendered_slides_en"][0]
            == f"/api/carousels/{sample_project.id}/slide-images/en/slide_1"
        )

    def test_generate_design_tokens_swipe_text_pt(self, sample_project):
        """Should use Portuguese swipe text for pt-BR language."""
        tokens = CarouselTemplateBuilder.generate_design_tokens(sample_project)

        assert tokens["layout"]["swipe_text"] == "Deslize \u2192"

    def test_generate_design_tokens_swipe_text_en(self):
        """Should use English swipe text for en language."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
            language="en",
        )
        tokens = CarouselTemplateBuilder.generate_design_tokens(project)

        assert tokens["layout"]["swipe_text"] == "Swipe \u2192"

    def test_generate_design_tokens_developer_skills(self):
        """Should generate correct design tokens for developer_skills theme."""
        project = CarouselProject(
            topic="Dev Skills",
            audience="Developers",
            niche="Tech",
            theme=CarouselTheme.DEVELOPER_SKILLS,
        )
        tokens = CarouselTemplateBuilder.generate_design_tokens(project)

        assert tokens["colors"]["primary"] == "#0ac5a8"
        assert tokens["colors"]["accent"] == "#8b5cf6"

    def test_generate_design_tokens_border_and_glow(self, sample_project):
        """Should generate border and glow colors based on primary."""
        tokens = CarouselTemplateBuilder.generate_design_tokens(sample_project)

        assert tokens["colors"]["border"] == "#3b82f633"
        assert tokens["colors"]["glow"] == "#3b82f60D"

    def test_generate_design_tokens_slides_config_7_slides(self):
        """Should use slides_config for 7_slides format."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
            slides_config="7_slides",
        )
        tokens = CarouselTemplateBuilder.generate_design_tokens(project)
        assert len(tokens["images"]["slides"]) == 7
        assert tokens["layout"]["progress_segments"] == 7

    def test_generate_design_tokens_slides_config_6_slides(self):
        """Should use slides_config for 6_slides format."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
            slides_config="6_slides",
        )
        tokens = CarouselTemplateBuilder.generate_design_tokens(project)
        assert len(tokens["images"]["slides"]) == 6
        assert tokens["layout"]["progress_segments"] == 6

    def test_generate_design_tokens_slides_config_comma_format(self):
        """Should use slides_config for comma format."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
            slides_config="1 intro, 2 content, 1 closing, 1 cta",
        )
        tokens = CarouselTemplateBuilder.generate_design_tokens(project)
        assert len(tokens["images"]["slides"]) == 5
        assert tokens["layout"]["progress_segments"] == 5

    def test_generate_design_tokens_invalid_slides_config(self):
        """Should fall back to MAX_SLIDES for unparseable config."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
            slides_config="something_wrong",
        )
        tokens = CarouselTemplateBuilder.generate_design_tokens(project)
        assert len(tokens["images"]["slides"]) == 7
        assert tokens["layout"]["progress_segments"] == 7

    def test_theme_pallets_constant_has_all_themes(self):
        """Should have all 5 theme palettes defined."""
        assert "cybersecurity" in THEME_PALETTES
        assert "ai_competition" in THEME_PALETTES
        assert "developer_skills" in THEME_PALETTES
        assert "source_code" in THEME_PALETTES
        assert "social_engineering" in THEME_PALETTES

    def test_theme_pallets_all_have_primary_accent_background(self):
        """Each theme should have primary, accent, and background keys."""
        for theme_name, theme in THEME_PALETTES.items():
            assert "primary" in theme, f"Theme {theme_name} missing primary"
            assert "accent" in theme, f"Theme {theme_name} missing accent"
            assert "background" in theme, f"Theme {theme_name} missing background"

    def test_build_carousel_html_summary_slide_has_hero_layout(
        self, sample_project, sample_theme
    ):
        """Should render summary slide with hero-bg layout."""
        slides = [
            {
                "number": "2",
                "type": "summary",
                "heading": "Resumo em 30 segundos",
                "body": "Summary body text",
            },
        ]

        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )

        assert "slide-hero-bg-img" in html
        assert "slide-hero-bg-gradient" in html
        assert "slide-hero-content" in html
        assert "Resumo em 30 segundos" in html
        assert "Summary body text" in html
        assert "02" in html

    def test_build_carousel_html_summary_slide_without_body(
        self, sample_project, sample_theme
    ):
        """Should render summary slide without body paragraph when body is empty."""
        slides = [
            {"number": "2", "type": "summary", "heading": "Resumo", "body": ""},
        ]

        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )

        assert '<p class="slide-hero-body">' not in html

    def test_build_carousel_html_intro_with_tldr(self, sample_project, sample_theme):
        """Should render s1-tldr on intro slide when present."""
        slides = [
            {
                "number": "1",
                "type": "intro",
                "heading": "Intro",
                "body": "Body",
                "tldr_strip": "Código vazou com malware: 2.3M downloads em 72h.",
            },
        ]

        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )

        assert 'class="s1-tldr">' in html
        assert "Código vazou com malware" in html

    def test_build_carousel_html_intro_without_tldr(self, sample_project, sample_theme):
        """Should not render s1-tldr element on intro slide when absent."""
        slides = [
            {"number": "1", "type": "intro", "heading": "Intro", "body": "Body"},
        ]

        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )

        assert 'class="s1-tldr">' not in html
