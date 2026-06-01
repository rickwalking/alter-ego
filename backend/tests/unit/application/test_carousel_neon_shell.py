"""Unit tests for Neon Shell v2.0 HTML output."""

import pytest

from rag_backend.application.services.carousel_template import CarouselTemplateBuilder


@pytest.mark.unit
class TestNeonShellHtml:
    """Tests for Neon Shell v2.0 HTML template output."""

    def test_build_carousel_html_has_grid_background(
        self, sample_project, sample_theme
    ):
        """Should render animated grid background."""
        slides = [
            {"number": "1", "type": "intro", "heading": "H", "body": "B"},
        ]
        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )
        assert 'class="grid-bg"' in html
        assert 'class="grid-bg-inner"' in html
        assert "grid-drift" in html

    def test_build_carousel_html_has_scanline_in_css(
        self, sample_project, sample_theme
    ):
        """Should render scanline overlay via body::after in CSS."""
        slides = [
            {"number": "1", "type": "intro", "heading": "H", "body": "B"},
        ]
        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )
        assert 'class="scanline-overlay"' not in html
        assert "body::after" in html
        assert "repeating-linear-gradient" in html

    def test_build_carousel_html_has_page_header(self, sample_project, sample_theme):
        """Should render page header with title and slide count."""
        slides = [
            {"number": "1", "type": "intro", "heading": "H", "body": "B"},
            {"number": "2", "type": "content", "heading": "C", "body": "B"},
        ]
        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )
        assert 'class="page-header"' in html
        assert sample_project.title in html
        assert "2 slides" in html
        assert 'class="sub"' in html

    def test_build_carousel_html_has_neon_shell_fonts(
        self, sample_project, sample_theme
    ):
        """Should import Inter and JetBrains Mono from Google Fonts."""
        slides = [
            {"number": "1", "type": "intro", "heading": "H", "body": "B"},
        ]
        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )
        assert "fonts.googleapis.com" in html
        assert "Inter" in html
        assert "JetBrains Mono" in html
        assert "preconnect" in html

    def test_build_carousel_html_intro_has_badge_dot(
        self, sample_project, sample_theme
    ):
        """Intro badge should include pulsing dot indicator."""
        slides = [
            {"number": "1", "type": "intro", "heading": "H", "body": "B"},
        ]
        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )
        assert 'class="s1-badge-dot"' in html
        assert "pulse-dot" in html

    def test_build_carousel_html_has_action_bar(self, sample_project, sample_theme):
        """Each slide should have Instagram-style action bar."""
        slides = [
            {"number": "1", "type": "intro", "heading": "H", "body": "B"},
        ]
        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )
        assert 'class="action-bar"' in html
        assert 'class="action-btn"' in html
        assert 'aria-label="Curtir"' in html

    def test_build_carousel_html_has_slide_counter(self, sample_project, sample_theme):
        """Should render slide counter dots with counter-label."""
        slides = [
            {"number": "1", "type": "intro", "heading": "H", "body": "B"},
            {"number": "2", "type": "content", "heading": "C", "body": "B"},
        ]
        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )
        assert 'class="slide-counter"' in html
        assert 'class="counter-dot active"' in html
        assert 'class="counter-dot past"' in html
        assert 'class="counter-label"' in html
        assert "1/2" in html

    def test_build_carousel_html_watermark_when_creator_set(
        self, sample_project, sample_theme
    ):
        """Should render watermark when creator metadata is present."""
        sample_project.creator_name = "Neon Shell"
        sample_project.creator_handle = "neonshell"
        sample_project.creator_avatar_url = "https://example.com/avatar.png"
        slides = [
            {"number": "1", "type": "intro", "heading": "H", "body": "B"},
        ]
        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )
        assert 'class="creator-watermark"' in html
        assert 'class="creator-watermark-avatar"' in html
        assert 'class="creator-watermark-text"' in html
        assert 'class="creator-watermark-name"' in html
        assert 'class="creator-watermark-handle"' in html
        assert "Neon Shell" in html
        assert "@neonshell" in html
        assert "avatar.png" in html

    def test_build_carousel_html_omits_watermark_when_no_creator(
        self, sample_project, sample_theme
    ):
        """Should omit watermark when no creator metadata."""
        sample_project.creator_name = None
        slides = [
            {"number": "1", "type": "intro", "heading": "H", "body": "B"},
        ]
        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )
        assert 'class="creator-watermark"' not in html

    def test_build_carousel_html_dark_class_on_html(self, sample_project, sample_theme):
        """HTML element should have dark class."""
        slides = [
            {"number": "1", "type": "intro", "heading": "H", "body": "B"},
        ]
        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )
        assert '<html class="dark"' in html

    def test_build_carousel_html_feed_container(self, sample_project, sample_theme):
        """Should wrap slides in feed container."""
        slides = [
            {"number": "1", "type": "intro", "heading": "H", "body": "B"},
        ]
        html = CarouselTemplateBuilder.build_carousel_html(
            sample_project, slides, sample_theme
        )
        assert 'class="feed"' in html
        assert 'class="ig-post"' in html
        assert 'class="ig-slide"' in html
        assert 'class="ig-slide-inner"' in html

    def test_carousel_project_has_template_version(self):
        """CarouselProject should default to v2 template."""
        from rag_backend.domain.models import CarouselProject

        project = CarouselProject(
            topic="Test",
            audience="All",
            niche="Tech",
        )
        assert project.template_version == "v2"

    def test_carousel_project_creator_fields(self):
        """CarouselProject should have creator metadata fields."""
        from rag_backend.domain.models import CarouselProject

        project = CarouselProject(
            topic="Test",
            audience="All",
            niche="Tech",
            creator_name="Dev",
            creator_handle="@dev",
            creator_avatar_url="https://a.com/x.png",
        )
        assert project.creator_name == "Dev"
        assert project.creator_handle == "@dev"
        assert project.creator_avatar_url == "https://a.com/x.png"
