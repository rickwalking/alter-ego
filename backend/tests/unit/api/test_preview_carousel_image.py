"""Unit tests for preview_carousel_image HD fallback and filename validation.

Gherkin: tests/features/carousel_image_refinement.feature
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from rag_backend.api.routes.carousels.preview import (
    _resolve_blog_preview_titles,
    _swipe_text_for_language,
    preview_carousel_image,
)
from rag_backend.domain.constants.blog_language import (
    BLOG_LANGUAGE_EN,
    CAROUSEL_SWIPE_TEXT_EN,
    CAROUSEL_SWIPE_TEXT_PT,
)
from rag_backend.domain.models import CarouselProject, User
from rag_backend.domain.models.user import UserRole


def _mock_request() -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/carousels/test/preview/images/slide_1.jpg",
        "headers": [],
        "query_string": b"",
        "server": ("test", 80),
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.unit
class TestPreviewCarouselImageFallback:
    """HD → standard → hero fallback chain."""

    async def _call_endpoint(
        self,
        tmp_path: Path,
        filename: str = "slide_1.jpg",
        lang: str = "pt",
        patched_resolve: list[Path | None] | None = None,
        mock_resolve_image_file: bool = True,
    ) -> object:
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            output_dir=str(tmp_path),
        )
        user = User(
            id=uuid4(),
            email="t@example.com",
            full_name="Test",
            role=UserRole.EDITOR,
            hashed_password="hash",
        )
        request = _mock_request()
        # The AE-0120 thin route reads the project + assigned-reviewer id through
        # the presentation handlers; the serving fallback (HD → standard → hero on
        # ``_resolve_image_file``) and access check stay at the route edge.
        handlers = MagicMock()
        handlers.get_project = AsyncMock(return_value=project)
        handlers.get_assigned_reviewer_id = AsyncMock(return_value=None)

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "rag_backend.api.routes.carousels.preview.assert_carousel_project_access",
                )
            )
            mock_resolve = None
            if mock_resolve_image_file:
                mock_resolve = stack.enter_context(
                    patch(
                        "rag_backend.api.routes.carousels.preview._resolve_image_file",
                        side_effect=patched_resolve or [None, None, None],
                    )
                )

            response = await preview_carousel_image(
                request=request,
                project_id=project.id,
                filename=filename,
                user=user,
                handlers=handlers,
                lang=lang,
            )
            return response, mock_resolve

    # Scenario: HD image is served when available
    async def test_serves_hd_when_present(self, tmp_path: Path) -> None:
        hd_file = tmp_path / "pt" / "hd" / "slide_1.jpg"
        hd_file.parent.mkdir(parents=True, exist_ok=True)
        hd_file.write_text("hd-content")

        response, mock_resolve = await self._call_endpoint(
            tmp_path,
            patched_resolve=[hd_file, None, None],
        )

        assert mock_resolve.call_count == 1
        assert mock_resolve.call_args_list[0][0][0] == tmp_path / "pt" / "hd"
        assert response.path == str(hd_file)

    # Scenario: Standard image is served when HD is missing
    async def test_falls_back_to_standard_when_hd_missing(self, tmp_path: Path) -> None:
        std_file = tmp_path / "pt" / "slide_1.jpg"
        std_file.parent.mkdir(parents=True, exist_ok=True)
        std_file.write_text("std-content")

        response, mock_resolve = await self._call_endpoint(
            tmp_path,
            patched_resolve=[None, std_file, None],
        )

        assert mock_resolve.call_count == 2
        assert mock_resolve.call_args_list[0][0][0] == tmp_path / "pt" / "hd"
        assert mock_resolve.call_args_list[1][0][0] == tmp_path / "pt"
        assert response.path == str(std_file)

    # Scenario: Hero image is served when both HD and standard are missing
    async def test_falls_back_to_hero_when_both_missing(self, tmp_path: Path) -> None:
        hero_file = tmp_path / "images" / "slide_1.jpg"
        hero_file.parent.mkdir(parents=True, exist_ok=True)
        hero_file.write_text("hero-content")

        response, mock_resolve = await self._call_endpoint(
            tmp_path,
            patched_resolve=[None, None, hero_file],
        )

        assert mock_resolve.call_count == 3
        assert mock_resolve.call_args_list[2][0][0] == tmp_path / "images"
        assert response.path == str(hero_file)

    # Scenario: Returns 404 when no image exists in any tier
    async def test_raises_404_when_no_image_found(self, tmp_path: Path) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _, _ = await self._call_endpoint(
                tmp_path,
                patched_resolve=[None, None, None],
            )
        assert exc_info.value.status_code == 404

    # Scenario: Rejects path-traversal filename patterns
    async def test_rejects_path_traversal_filename(self, tmp_path: Path) -> None:
        # When calling the handler directly FastPath validation is bypassed,
        # but _resolve_image_file internally sanitizes the filename and
        # raises HTTPException(404) before any file access occurs.
        with pytest.raises(HTTPException) as exc_info:
            _, _ = await self._call_endpoint(
                tmp_path,
                filename="../../../etc/passwd",
                mock_resolve_image_file=False,
            )
        assert exc_info.value.status_code == 404

    # Scenario: Accepts safe filenames with hyphens, underscores, and dots
    async def test_accepts_safe_filename(self, tmp_path: Path) -> None:
        safe_file = tmp_path / "pt" / "hd" / "slide_1-2.jpg"
        safe_file.parent.mkdir(parents=True, exist_ok=True)
        safe_file.write_text("safe")

        response, _ = await self._call_endpoint(
            tmp_path,
            filename="slide_1-2.jpg",
            patched_resolve=[safe_file, None, None],
        )
        assert response.path == str(safe_file)


class TestResolveBlogPreviewTitles:
    """Unit tests for _resolve_blog_preview_titles."""

    def _make_project(self, **kwargs: object) -> MagicMock:
        project = MagicMock()
        project.title = kwargs.get("title", "Default Title")
        project.title_en = kwargs.get("title_en")
        project.subtitle = kwargs.get("subtitle")
        project.subtitle_en = kwargs.get("subtitle_en")
        project.topic = kwargs.get("topic", "Default Topic")
        return project

    def test_en_with_translated_title(self) -> None:
        """Given English lang with translated title, when resolving, then translated title is used."""
        project = self._make_project(title="PT Title", title_en="EN Title")
        title, subtitle = _resolve_blog_preview_titles("en", "# Translated", project)
        assert title == "Translated"
        assert subtitle is None

    def test_en_with_title_en_fallback(self) -> None:
        """Given English lang with no translation, when resolving, then title_en is used."""
        project = self._make_project(title="PT Title", title_en="EN Title")
        title, subtitle = _resolve_blog_preview_titles("en", "Body", project)
        assert title == "EN Title"

    def test_en_with_title_fallback(self) -> None:
        """Given English lang with no title_en, when resolving, then title is used."""
        project = self._make_project(title="PT Title")
        title, subtitle = _resolve_blog_preview_titles("en", "Body", project)
        assert title == "PT Title"

    def test_en_with_topic_fallback(self) -> None:
        """Given English lang with no title, when resolving, then topic is used."""
        project = self._make_project(title=None, topic="Topic")
        title, subtitle = _resolve_blog_preview_titles("en", "Body", project)
        assert title == "Topic"

    def test_en_with_subtitle_en_fallback(self) -> None:
        """Given English lang with subtitle_en, when resolving, then subtitle_en is used."""
        project = self._make_project(subtitle_en="EN Subtitle")
        title, subtitle = _resolve_blog_preview_titles("en", "Body", project)
        assert subtitle == "EN Subtitle"

    def test_en_with_first_paragraph_fallback(self) -> None:
        """Given English lang with no subtitle_en, when resolving, then first paragraph is used."""
        project = self._make_project()
        title, subtitle = _resolve_blog_preview_titles("en", "First paragraph", project)
        assert subtitle == "First paragraph"

    def test_en_with_subtitle_fallback(self) -> None:
        """Given English lang with no first paragraph, when resolving, then subtitle is used."""
        project = self._make_project(subtitle="Subtitle")
        title, subtitle = _resolve_blog_preview_titles("en", "# Title", project)
        assert subtitle == "Subtitle"

    def test_pt_with_translated_title(self) -> None:
        """Given PT lang with translated title, when resolving, then translated title is used."""
        project = self._make_project(title="PT Title")
        title, subtitle = _resolve_blog_preview_titles("pt", "# Translated", project)
        assert title == "Translated"
        assert subtitle is None

    def test_pt_with_title_fallback(self) -> None:
        """Given PT lang with no translation, when resolving, then title is used."""
        project = self._make_project(title="PT Title")
        title, subtitle = _resolve_blog_preview_titles("pt", "Body", project)
        assert title == "PT Title"

    def test_pt_with_topic_fallback(self) -> None:
        """Given PT lang with no title, when resolving, then topic is used."""
        project = self._make_project(title=None, topic="Topic")
        title, subtitle = _resolve_blog_preview_titles("pt", "Body", project)
        assert title == "Topic"

    def test_pt_with_subtitle_fallback(self) -> None:
        """Given PT lang with no translated subtitle, when resolving, then subtitle is used."""
        project = self._make_project(subtitle="Subtitle")
        title, subtitle = _resolve_blog_preview_titles("pt", "# Title", project)
        assert subtitle == "Subtitle"


class TestSwipeTextForLanguage:
    """Unit tests for _swipe_text_for_language."""

    def test_returns_english_text_for_en(self) -> None:
        """Given English language code, when getting swipe text, then English text is returned."""
        result = _swipe_text_for_language(BLOG_LANGUAGE_EN)
        assert result == CAROUSEL_SWIPE_TEXT_EN

    def test_returns_portuguese_text_for_other(self) -> None:
        """Given non-English language code, when getting swipe text, then Portuguese text is returned."""
        result = _swipe_text_for_language("pt")
        assert result == CAROUSEL_SWIPE_TEXT_PT

    def test_returns_portuguese_text_for_es(self) -> None:
        """Given Spanish language code, when getting swipe text, then Portuguese text is returned."""
        result = _swipe_text_for_language("es")
        assert result == CAROUSEL_SWIPE_TEXT_PT
