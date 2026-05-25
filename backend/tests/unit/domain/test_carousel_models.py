"""Unit tests for carousel domain models and design tokens."""

import pytest

from rag_backend.domain.models import (
    CarouselProject,
    CarouselTheme,
    DesignTokenColors,
    DesignTokenImages,
    DesignTokenLayout,
    DesignTokens,
    DesignTokenTypography,
)


@pytest.mark.unit
class TestCarouselProjectBlogMethods:
    """Tests for CarouselProject blog i18n methods."""

    def test_get_blog_returns_pt_from_translations(self):
        """Should return Portuguese blog from translations."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
        )
        project.blog_markdown = "# PT Default\n\nConteudo."
        project.blog_translations = {
            "pt": "# PT\n\nConteudo em portugues.",
            "en": "# EN\n\nContent in English.",
        }

        result = project.get_blog("pt")
        assert result == "# PT\n\nConteudo em portugues."

    def test_get_blog_returns_en_from_translations(self):
        """Should return English blog from translations."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
        )
        project.blog_markdown = "# PT Default\n\nConteudo."
        project.blog_translations = {
            "pt": "# PT\n\nConteudo em portugues.",
            "en": "# EN\n\nContent in English.",
        }

        result = project.get_blog("en")
        assert result == "# EN\n\nContent in English."

    def test_get_blog_returns_default_when_no_translations(self):
        """Should return blog_markdown as fallback when no translations."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
        )
        project.blog_markdown = "# PT Default\n\nConteudo."

        result = project.get_blog("pt")
        assert result == "# PT Default\n\nConteudo."

    def test_get_blog_returns_none_when_no_content(self):
        """Should return None when no blog content exists."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
        )

        result = project.get_blog("pt")
        assert result is None

    def test_get_available_languages_with_translations(self):
        """Should return language keys from translations dict."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
        )
        project.blog_translations = {"pt": "content", "en": "content"}

        langs = project.get_available_languages()
        assert "pt" in langs
        assert "en" in langs

    def test_get_available_languages_with_default_only(self):
        """Should return pt when only blog_markdown exists."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
        )
        project.blog_markdown = "# Content"

        langs = project.get_available_languages()
        assert langs == ["pt"]

    def test_get_available_languages_with_no_content(self):
        """Should return empty list when no blog content."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
        )

        langs = project.get_available_languages()
        assert langs == []


@pytest.mark.unit
class TestCarouselProjectDesignMethods:
    """Tests for CarouselProject design token methods."""

    def test_get_design_returns_tokens(self):
        """Should return design tokens when set."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
        )
        design_tokens: DesignTokens = DesignTokens(
            colors=DesignTokenColors(
                primary="#3b82f6",
                accent="#f59e0b",
                bg="#0a0e17",
                text="#ffffff",
                text_muted="rgba(255,255,255,0.63)",
                text_dim="rgba(255,255,255,0.48)",
                border="#3b82f633",
                glow="#3b82f60D",
            ),
            typography=DesignTokenTypography(
                font_family_heading="'Segoe UI', Arial, sans-serif",
                font_family_body="'Segoe UI', Arial, sans-serif",
                font_family_badge="'Courier New', monospace",
            ),
            images=DesignTokenImages(
                hero="/api/carousels/test/images/hero",
                slides=["/api/carousels/test/images/slide_1"],
            ),
            layout=DesignTokenLayout(
                badge_label="Tech",
                swipe_text="Deslize \u2192",
                progress_segments=7,
            ),
        )
        project.design_tokens = design_tokens

        result = project.get_design()
        assert result is not None
        assert result["colors"]["primary"] == "#3b82f6"
        assert result["layout"]["progress_segments"] == 7

    def test_get_design_returns_none_when_not_set(self):
        """Should return None when design tokens not set."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
        )

        assert project.get_design() is None

    def test_get_image_url_returns_api_url(self):
        """Should return API URL for carousel image."""

        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
        )
        project.output_dir = "/tmp/carousels/test"

        url = project.get_image_url("slide_1.jpg")
        assert url == f"/api/carousels/{project.id}/images/slide_1.jpg"

    def test_get_image_url_returns_none_when_no_output_dir(self):
        """Should return None when output_dir is not set."""
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            theme=CarouselTheme.AI_COMPETITION,
        )

        assert project.get_image_url("slide_1.jpg") is None


@pytest.mark.unit
class TestDesignTokensTypedDicts:
    """Tests for DesignTokens TypedDict structures."""

    def test_design_tokens_colors_structure(self):
        """Should accept all required color fields."""
        colors = DesignTokenColors(
            primary="#3b82f6",
            accent="#f59e0b",
            bg="#0a0e17",
            text="#ffffff",
            text_muted="rgba(255,255,255,0.63)",
            text_dim="rgba(255,255,255,0.48)",
            border="#3b82f633",
            glow="#3b82f60D",
        )
        assert colors["primary"] == "#3b82f6"
        assert colors["border"] == "#3b82f633"

    def test_design_tokens_typography_structure(self):
        """Should accept all required typography fields."""
        typography = DesignTokenTypography(
            font_family_heading="'Segoe UI', Arial, sans-serif",
            font_family_body="'Segoe UI', Arial, sans-serif",
            font_family_badge="'Courier New', monospace",
        )
        assert typography["font_family_heading"] == "'Segoe UI', Arial, sans-serif"

    def test_design_tokens_images_structure(self):
        """Should accept hero and slides image URLs."""
        images = DesignTokenImages(
            hero="/api/carousels/123/images/hero",
            slides=["/api/carousels/123/images/slide_1"],
        )
        assert images["hero"] == "/api/carousels/123/images/hero"
        assert len(images["slides"]) == 1

    def test_design_tokens_layout_structure(self):
        """Should accept badge label, swipe text, progress segments."""
        layout = DesignTokenLayout(
            badge_label="AI",
            swipe_text="Deslize \u2192",
            progress_segments=7,
        )
        assert layout["badge_label"] == "AI"
        assert layout["progress_segments"] == 7

    def test_complete_design_tokens(self):
        """Should construct full DesignTokens from all sub-tokens."""
        tokens = DesignTokens(
            colors=DesignTokenColors(
                primary="#3b82f6",
                accent="#f59e0b",
                bg="#0a0e17",
                text="#ffffff",
                text_muted="rgba(255,255,255,0.63)",
                text_dim="rgba(255,255,255,0.48)",
                border="#3b82f633",
                glow="#3b82f60D",
            ),
            typography=DesignTokenTypography(
                font_family_heading="'Segoe UI', Arial, sans-serif",
                font_family_body="'Segoe UI', Arial, sans-serif",
                font_family_badge="'Courier New', monospace",
            ),
            images=DesignTokenImages(
                hero="/api/carousels/abc/images/hero",
                slides=["/api/carousels/abc/images/slide_1"],
            ),
            layout=DesignTokenLayout(
                badge_label="AI",
                swipe_text="Deslize \u2192",
                progress_segments=7,
            ),
        )
        assert tokens["colors"]["primary"] == "#3b82f6"
        assert tokens["typography"]["font_family_badge"] == "'Courier New', monospace"
        assert tokens["images"]["hero"] == "/api/carousels/abc/images/hero"
        assert tokens["layout"]["progress_segments"] == 7
