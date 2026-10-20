"""AE-0439 (QA F-14): blog-image 404s are never cached at the edge.

Handler-level (no HTTP transport), like ``test_blog_post_read_handler_ae0428``.

Gherkin: tests/features/blog_carousel_minors_ae0439.feature
  - Scenario: An anonymous draft blog image 404 is never cached
"""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse

import rag_backend.api.routes.blog_post_images as image_routes
from rag_backend.api.routes.blog_post_images import (
    ImageFileTarget,
)
from rag_backend.domain.constants.blog_post import BlogPostStatus

POST_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
FILE = "337aacd2-0000-4000-8000-000000000001.png"
CACHE_CONTROL_HEADER = "Cache-Control"
NO_STORE = "no-store"


def _handler():  # noqa: ANN202
    """The route function itself (slowapi wraps it; unwrap for a direct call)."""
    return inspect.unwrap(image_routes.get_blog_image)


def _target(filename: str = FILE, user: object = None) -> ImageFileTarget:
    return ImageFileTarget(
        post_id=POST_ID,
        filename=filename,
        db=cast(object, MagicMock()),
        user=user,
    )


def _row(status: str, author_id: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(status=status, author_id=author_id)


@pytest.mark.unit
@pytest.mark.asyncio
class TestBlogImageNotFoundCache:
    async def test_an_anonymous_draft_404_is_no_store(self) -> None:
        """Scenario: An anonymous draft blog image 404 is never cached."""
        with patch(
            "rag_backend.api.routes.blog_post_images.get_blog_post_by_id",
            AsyncMock(return_value=_row(BlogPostStatus.DRAFT.value, "author")),
        ):
            with pytest.raises(HTTPException) as info:
                await _handler()(request=None, target=_target())
        assert info.value.status_code == 404
        assert info.value.headers[CACHE_CONTROL_HEADER] == NO_STORE

    async def test_a_missing_file_404_is_no_store(self) -> None:
        store = MagicMock()
        store.file_for = MagicMock(return_value=None)
        with (
            patch(
                "rag_backend.api.routes.blog_post_images.get_blog_post_by_id",
                AsyncMock(return_value=_row(BlogPostStatus.PUBLISHED.value)),
            ),
            patch(
                "rag_backend.api.routes.blog_post_images.blog_images_store",
                return_value=store,
            ),
        ):
            with pytest.raises(HTTPException) as info:
                await _handler()(request=None, target=_target())
        assert info.value.status_code == 404
        assert info.value.headers[CACHE_CONTROL_HEADER] == NO_STORE

    async def test_an_invalid_filename_404_is_no_store(self) -> None:
        with pytest.raises(HTTPException) as info:
            await _handler()(
                request=None, target=_target(filename="../../etc/passwd")
            )
        assert info.value.status_code == 404
        assert info.value.headers[CACHE_CONTROL_HEADER] == NO_STORE

    async def test_an_author_draft_image_keeps_private_no_store(
        self, tmp_path: Path
    ) -> None:
        """The author's 200 keeps its existing private header (unchanged)."""
        stored = tmp_path / FILE
        stored.write_bytes(b"png")
        store = MagicMock()
        store.file_for = MagicMock(return_value=stored)
        user = SimpleNamespace(id="author", is_admin=MagicMock(return_value=False))
        with (
            patch(
                "rag_backend.api.routes.blog_post_images.get_blog_post_by_id",
                AsyncMock(return_value=_row(BlogPostStatus.DRAFT.value, "author")),
            ),
            patch(
                "rag_backend.api.routes.blog_post_images.blog_images_store",
                return_value=store,
            ),
        ):
            response = await _handler()(
                request=None, target=_target(user=user)
            )
        assert isinstance(response, FileResponse)
        assert response.headers[CACHE_CONTROL_HEADER] == "private, no-store"
