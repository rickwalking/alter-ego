"""Unit tests for editorial distribution pack helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.editorial_distribution_constants import (
    OUTLINE_LEGACY_BODY_KEY,
    OUTLINE_LEGACY_HEADING_KEY,
)
from rag_backend.application.services.carousel.editorial_distribution_pack import (
    build_blog_markdown_en_from_translations,
    build_blog_markdown_from_drafts,
    build_editorial_distribution_updates,
)
from rag_backend.domain.constants.carousel import CAROUSEL_SLIDES_CONFIG_SEVEN
from rag_backend.domain.models import CarouselProject, CarouselStatus


class TestBuildBlogMarkdownFromDrafts:
    def test_builds_sections_from_drafts(self) -> None:
        drafts = [
            {
                "slide_index": 1,
                "title": "Intro",
                "draft_text": "Hook body.",
            },
            {
                "slide_index": 2,
                "title": "Deep dive",
                "draft_text": "Main insight.",
            },
        ]
        markdown = build_blog_markdown_from_drafts(drafts, title="My Topic")
        assert "# My Topic" in markdown
        assert "## Intro" in markdown
        assert "Hook body." in markdown
        assert "## Deep dive" in markdown

    def test_skips_slides_without_body(self) -> None:
        drafts = [{"slide_index": 1, "title": "Empty", "draft_text": "   "}]
        markdown = build_blog_markdown_from_drafts(drafts, title="T")
        assert "## Empty" not in markdown


class TestBuildBlogMarkdownEn:
    def test_uses_en_translation_body(self) -> None:
        drafts = [{"slide_index": 1, "title": "PT Hook", "draft_text": "Corpo PT."}]
        translations = {
            1: {
                OUTLINE_LEGACY_HEADING_KEY: "EN Hook",
                OUTLINE_LEGACY_BODY_KEY: "EN body.",
            }
        }
        markdown = build_blog_markdown_en_from_translations(
            drafts, translations, title="EN Title"
        )
        assert "## EN Hook" in markdown
        assert "EN body." in markdown
        assert "Corpo PT." not in markdown


@pytest.mark.asyncio
async def test_build_editorial_distribution_updates_persists_fields() -> None:
    """Distribution pack writes caption, blog, and slides_config to the project."""
    project_id = uuid4()
    project = CarouselProject(
        id=project_id,
        topic="Topic",
        audience="Devs",
        niche="Tech",
        status=CarouselStatus.DRAFTING,
        output_dir=f"/tmp/{project_id}",
    )
    slide_drafts = [
        {"slide_index": 1, "title": "Hook", "draft_text": "Body one."},
    ]
    outline = [
        {"slide_index": 1, "title": "Hook", "key_points": [], "slide_type": "intro"}
    ]

    mock_repo = MagicMock()
    mock_repo.get_project_by_id = AsyncMock(return_value=project)
    mock_repo.get_slides_by_project = AsyncMock(return_value=[])
    mock_repo.create_slide = AsyncMock()
    mock_repo.update_project = AsyncMock(side_effect=lambda p: p)

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Caption #tag"))

    with (
        patch(
            "rag_backend.application.services.carousel.editorial_distribution_pack.PostgresCarouselRepository",
            return_value=mock_repo,
        ),
        patch(
            "rag_backend.application.services.carousel.editorial_distribution_pack._generate_en_translations",
            new=AsyncMock(return_value={1: {"heading": "Hook", "body": "Body one."}}),
        ),
    ):
        updates = await build_editorial_distribution_updates(
            MagicMock(),
            mock_llm,
            str(project_id),
            outline,
            slide_drafts,
            linkedin_generator=None,
        )

    assert updates["caption"] == "Caption #tag"
    assert "Hook" in str(updates["blog_markdown"])
    assert project.slides_config == CAROUSEL_SLIDES_CONFIG_SEVEN
    mock_repo.update_project.assert_called()
