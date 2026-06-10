"""Unit tests for blog composition from long-form notes."""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.blog_composition import (
    BlogCompositionInput,
    build_blog_markdown_en_from_long_form_notes,
    build_blog_markdown_from_long_form_notes,
)
from rag_backend.application.services.carousel.editorial_distribution_constants import (
    LONG_FORM_NOTES_KEY,
    OUTLINE_LEGACY_HEADING_KEY,
)


@pytest.mark.unit
class TestBlogComposition:
    """Gherkin: long_form_notes are available for blog generation."""

    def test_builds_sections_from_long_form_notes(self) -> None:
        composition = BlogCompositionInput(
            slides=(
                {
                    "slide_index": 1,
                    "title": "Intro",
                    LONG_FORM_NOTES_KEY: "Expanded hook with context.",
                },
                {
                    "slide_index": 2,
                    "title": "Deep dive",
                    LONG_FORM_NOTES_KEY: "Detailed analysis paragraph.",
                },
            ),
            title="My Topic",
            research_summary="Research synthesis intro.",
            outline=(
                {"slide_index": 1, "title": "Intro"},
                {"slide_index": 2, "title": "Deep dive"},
            ),
        )
        markdown = build_blog_markdown_from_long_form_notes(composition)
        assert "# My Topic" in markdown
        assert "Research synthesis intro." in markdown
        assert "## Intro" in markdown
        assert "Expanded hook with context." in markdown
        assert "Detailed analysis paragraph." in markdown
        assert "Hook body." not in markdown

    def test_skips_slides_without_long_form_notes(self) -> None:
        composition = BlogCompositionInput(
            slides=({"slide_index": 1, "title": "Empty", "draft_text": "Short body."},),
            title="T",
        )
        markdown = build_blog_markdown_from_long_form_notes(composition)
        assert markdown == "# T"

    def test_en_blog_uses_translated_long_form_notes(self) -> None:
        composition = BlogCompositionInput(
            slides=(
                {
                    "slide_index": 1,
                    "title": "PT Hook",
                    LONG_FORM_NOTES_KEY: "Notas PT.",
                },
            ),
            title="EN Title",
        )
        translations = {
            1: {
                OUTLINE_LEGACY_HEADING_KEY: "EN Hook",
                LONG_FORM_NOTES_KEY: "EN long-form notes.",
            }
        }
        markdown = build_blog_markdown_en_from_long_form_notes(composition, translations)
        assert "## EN Hook" in markdown
        assert "EN long-form notes." in markdown
        assert "Notas PT." not in markdown
