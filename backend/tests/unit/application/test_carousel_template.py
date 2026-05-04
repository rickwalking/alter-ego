"""Unit tests for CarouselTemplateBuilder.

Gherkin: tests/features/carousel_design_refinement.feature
"""

import pytest

from rag_backend.application.services.carousel_template import (
    THEME_PALETTES,
    CarouselTemplateBuilder,
)
from rag_backend.domain.models import CarouselProject, CarouselTheme


@pytest.fixture
def sample_project():
    """Create a sample carousel project for testing."""
    project = CarouselProject(
        topic="Machine Learning Basics",
        audience="Beginners",
        niche="AI Education",
        theme=CarouselTheme.AI_COMPETITION,
    )
    project.set_title(title="Master ML in 7 Slides", subtitle="A beginner's guide")
    return project


@pytest.fixture
def sample_theme():
    """Create a sample theme dict for testing."""
    return {
        "primary": "#3b82f6",
        "accent": "#f59e0b",
        "background": "#0a0e17",
    }


@pytest.fixture
def sample_research_context():
    """Create sample research context text."""
    return (
        "Source: https://example.com/ml\nMachine learning is a subset of artificial intelligence..."
    )


@pytest.mark.unit
class TestCarouselTemplateBuilder:
    """Tests for CarouselTemplateBuilder."""

    def test_build_title_prompt_contains_project_info(
        self, sample_project, sample_research_context
    ):
        """Should include topic, audience, niche, and research context in title prompt."""
        prompt = CarouselTemplateBuilder.build_title_prompt(sample_project, sample_research_context)

        assert "Machine Learning Basics" in prompt
        assert "Beginners" in prompt
        assert "AI Education" in prompt
        assert "Research context" in prompt
        assert "JSON" in prompt

    def test_build_content_prompt_bilingual(self, sample_project, sample_research_context):
        """Should include bilingual content instructions."""
        prompt = CarouselTemplateBuilder.build_content_prompt(
            sample_project, sample_research_context
        )

        assert "TWO languages" in prompt
        assert "blog_pt" in prompt
        assert "blog_en" in prompt
        assert "title_pt" in prompt
        assert "title_en" in prompt
        assert "Brazilian Portuguese" in prompt

    def test_build_content_prompt_contains_project_context(
        self, sample_project, sample_research_context
    ):
        """Should include all project details and research in content prompt."""
        prompt = CarouselTemplateBuilder.build_content_prompt(
            sample_project, sample_research_context
        )

        assert "Master ML in 7 Slides" in prompt
        assert "A beginner's guide" in prompt
        assert "7-slide" in prompt

    def test_build_caption_prompt_contains_slide_summaries(self, sample_project):
        """Should include slide headings and title in caption prompt."""
        slide_headings = [
            (1, "What is ML?"),
            (2, "Supervised Learning"),
            (3, "Unsupervised Learning"),
        ]

        prompt = CarouselTemplateBuilder.build_caption_prompt(sample_project, slide_headings)

        assert "Master ML in 7 Slides" in prompt
        assert "Slide 1: What is ML?" in prompt
        assert "Slide 2: Supervised Learning" in prompt
        assert "hashtags" in prompt.lower()

    def test_build_carousel_html_contains_doctype(self, sample_project, sample_theme):
        """Should produce valid HTML with DOCTYPE declaration."""
        slides = [
            {"number": "1", "type": "intro", "heading": "Intro", "body": "Body"},
        ]

        html = CarouselTemplateBuilder.build_carousel_html(sample_project, slides, sample_theme)

        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_build_carousel_html_contains_css_variables(self, sample_project, sample_theme):
        """Should embed theme colors as CSS variables."""
        slides = [
            {"number": "1", "type": "intro", "heading": "Intro", "body": "Body"},
        ]

        html = CarouselTemplateBuilder.build_carousel_html(sample_project, slides, sample_theme)

        assert "--primary: #3b82f6" in html
        assert "--accent: #f59e0b" in html
        assert "--bg: #0a0e17" in html

    def test_build_carousel_html_contains_slide_content(self, sample_project, sample_theme):
        """Should include slide heading and body in HTML."""
        slides = [
            {
                "number": "1",
                "type": "intro",
                "heading": "Test Heading",
                "body": "Test Body",
            },
        ]

        html = CarouselTemplateBuilder.build_carousel_html(sample_project, slides, sample_theme)

        assert "Test Heading" in html
        assert "Test Body" in html

    def test_build_carousel_html_multiple_slides(self, sample_project, sample_theme):
        """Should render multiple slides in sequence."""
        slides = [
            {"number": "1", "type": "intro", "heading": "Intro", "body": "Intro body"},
            {"number": "2", "type": "content", "heading": "Content", "body": "Content body"},
            {"number": "3", "type": "cta", "heading": "CTA", "body": "CTA body"},
        ]

        html = CarouselTemplateBuilder.build_carousel_html(sample_project, slides, sample_theme)

        assert "Intro" in html
        assert "Content" in html
        assert "CTA" in html
        assert html.count('<div class="slide') >= 3

    def test_build_carousel_html_language_attribute(self, sample_project, sample_theme):
        """Should set correct language attribute on HTML element."""
        slides = [
            {"number": "1", "type": "intro", "heading": "H", "body": "B"},
        ]

        html = CarouselTemplateBuilder.build_carousel_html(sample_project, slides, sample_theme)

        assert 'lang="pt-BR"' in html

    def test_build_carousel_html_intro_slide_has_badge(self, sample_project, sample_theme):
        """Should render niche badge on intro slide."""
        slides = [
            {"number": "1", "type": "intro", "heading": "H", "body": "B"},
        ]

        html = CarouselTemplateBuilder.build_carousel_html(sample_project, slides, sample_theme)

        assert "AI Education" in html
        assert "s1-badge" in html

    def test_build_carousel_html_content_slide_has_progress(self, sample_project, sample_theme):
        """Should render progress bars on content slides."""
        slides = [
            {"number": "2", "type": "content", "heading": "H", "body": "B"},
        ]

        html = CarouselTemplateBuilder.build_carousel_html(sample_project, slides, sample_theme)

        assert "progress" in html
        assert "bar active" in html

    def test_build_carousel_html_cta_slide_has_buttons(self, sample_project, sample_theme):
        """Should render CTA buttons on cta slides."""
        slides = [
            {"number": "7", "type": "cta", "heading": "Save & Share", "body": "CTA"},
        ]

        html = CarouselTemplateBuilder.build_carousel_html(sample_project, slides, sample_theme)

        assert "cta-btn primary" in html
        assert "cta-btn secondary" in html
        assert "Salve" in html

    # Scenario: Design overrides are injected into HTML before </style>
    def test_build_carousel_html_injects_design_overrides(self, sample_project, sample_theme):
        """Should inject custom CSS before the closing </style> tag."""
        slides = [
            {"number": "1", "type": "intro", "heading": "Intro", "body": "Body"},
        ]
        override = ".hero-img { height: 500px; }"

        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme, design_overrides=override
        )

        assert override in html
        assert html.index(override) < html.index("</style>")

    # Scenario: No overrides block is emitted when design_overrides is None
    def test_build_carousel_html_omits_overrides_when_none(self, sample_project, sample_theme):
        """Should not contain an overrides block when None is passed."""
        slides = [
            {"number": "1", "type": "intro", "heading": "Intro", "body": "Body"},
        ]

        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme, design_overrides=None
        )

        assert "design overrides" not in html.lower()


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
        assert tokens["layout"]["progress_segments"] == 7

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

        # The hero image is the intro slide's rendered JPG (slide_1) —
        # there is no separate "hero" file on disk.
        # `hero` + `slides` reference the raw hero images (used by blog).
        assert tokens["images"]["hero"] == f"/api/carousels/{sample_project.id}/images/slide_1"
        assert len(tokens["images"]["slides"]) == 7
        assert tokens["images"]["slides"][0] == f"/api/carousels/{sample_project.id}/images/slide_1"
        # `rendered_slides_*` reference the post-Playwright JPGs with
        # text overlay (used by publish viewer).
        assert "rendered_slides_pt" in tokens["images"]
        assert (
            tokens["images"]["rendered_slides_pt"][0]
            == f"/api/carousels/{sample_project.id}/slide-images/pt/slide_1"
        )
        assert "rendered_slides_en" in tokens["images"]
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

    def test_build_carousel_html_summary_slide_has_points(self, sample_project, sample_theme):
        """Should render summary slide with summary_points cards."""
        slides = [
            {
                "number": "2",
                "type": "summary",
                "heading": "Resumo em 30 segundos",
                "body": "",
                "summary_points": [
                    {"icon": "🎯", "title": "Código vazou", "body": "Publicado por 6h"},
                    {"icon": "🔍", "title": "Malware embutido", "body": "Exfiltrou dados"},
                    {"icon": "⚡", "title": "2.3M afetados", "body": "Removido em 72h"},
                ],
            },
        ]

        html = CarouselTemplateBuilder.build_carousel_html(sample_project, slides, sample_theme)

        assert "summary-slide" in html
        assert "summary-grid" in html
        assert "summary-item" in html
        assert "🎯" in html
        assert "Código vazou" in html
        assert "Publicado por 6h" in html
        assert "02" in html

    def test_build_carousel_html_summary_slide_without_points(self, sample_project, sample_theme):
        """Should render summary slide without cards when no summary_points."""
        slides = [
            {"number": "2", "type": "summary", "heading": "Resumo", "body": ""},
        ]

        html = CarouselTemplateBuilder.build_carousel_html(sample_project, slides, sample_theme)

        assert "summary-slide" in html
        assert 'class="summary-item">' not in html

    def test_build_carousel_html_intro_with_tldr_strip(self, sample_project, sample_theme):
        """Should render tldr_strip on intro slide when present."""
        slides = [
            {
                "number": "1",
                "type": "intro",
                "heading": "Intro",
                "body": "Body",
                "tldr_strip": "Código vazou com malware: 2.3M downloads em 72h.",
            },
        ]

        html = CarouselTemplateBuilder.build_carousel_html(sample_project, slides, sample_theme)

        assert 'class="tldr-strip">' in html
        assert "Código vazou com malware" in html

    def test_build_carousel_html_intro_without_tldr_strip(self, sample_project, sample_theme):
        """Should not render tldr-strip element on intro slide when absent."""
        slides = [
            {"number": "1", "type": "intro", "heading": "Intro", "body": "Body"},
        ]

        html = CarouselTemplateBuilder.build_carousel_html(sample_project, slides, sample_theme)

        assert 'class="tldr-strip">' not in html

    def test_build_carousel_html_summary_slide_progress_bars(self, sample_project, sample_theme):
        """Summary slide should render 7 progress bars."""
        slides = [
            {"number": "2", "type": "summary", "heading": "Resumo", "body": ""},
        ]

        html = CarouselTemplateBuilder.build_carousel_html(sample_project, slides, sample_theme)

        # Count progress bars: should be 7 (MAX_SLIDES)
        assert html.count('class="bar ') == 7
        assert 'class="bar active"' in html
