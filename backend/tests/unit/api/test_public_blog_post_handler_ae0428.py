"""Public-read handler tests: strict read + uniform 404 mapping.

Covers ``get_public_blog_post`` at the handler level (no HTTP transport) so
the removed read fail-safe is proven on the exact lines its removal
changed: a published v2 row renders its public detail and a published non-v2
row fails closed with the uniform 404 (no existence leak, no legacy
adaptation).

Gherkin: tests/features/blog_sections_ae0423.feature
  - Scenario: A non-v2 read fails closed with the standard error/404
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from fastapi import HTTPException

import rag_backend.api.routes.public_blog_post as public_routes
from rag_backend.api.schemas.public_blog_post import PublicBlogPostResponse
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from tests.blog_v2_support import v2_content

POST_ID = "550e8400-e29b-41d4-a716-446655440000"
ERR_PUBLIC_BLOG_POST_NOT_FOUND = public_routes.ERR_PUBLIC_BLOG_POST_NOT_FOUND

GetPublicHandler = Callable[..., Awaitable[PublicBlogPostResponse]]


class _FakeRowResult:
    def __init__(self, row: BlogPostModel | None) -> None:
        self._row = row

    def scalar_one_or_none(self) -> BlogPostModel | None:
        return self._row


class _FakeDb:
    """AsyncSession stand-in whose ``execute`` returns the seeded row."""

    def __init__(self, row: BlogPostModel | None) -> None:
        self._row = row

    async def execute(self, *args: object, **kwargs: object) -> _FakeRowResult:
        return _FakeRowResult(self._row)


def _published_row(content: dict[str, object]) -> BlogPostModel:
    return BlogPostModel(
        id=POST_ID,
        project_id=None,
        origin="standalone",
        title="T",
        slug="t",
        status="published",
        content=content,
        author_id="550e8400-e29b-41d4-a716-446655440001",
        excerpt="Excerpt",
        featured_image_url="https://cdn.example/cover.jpg",
        published_at=datetime.now(UTC),
        meta_title=None,
        meta_description=None,
        keywords=["ai"],
        canonical_url=None,
    )


def _handler() -> GetPublicHandler:
    """The route function itself (slowapi wraps it; unwrap for a direct call)."""
    return cast(
        GetPublicHandler,
        inspect.unwrap(public_routes.get_public_blog_post),
    )


# Scenario: A published v2 row renders its public detail
@pytest.mark.asyncio
async def test_published_v2_row_returns_public_detail() -> None:
    row = _published_row(v2_content("Corpo"))

    result = await _handler()(
        request=None,
        post_id=UUID(POST_ID),
        db=_FakeDb(row),
    )

    assert result.id == UUID(POST_ID)
    assert result.content["sections"][0]["body_md"] == "Corpo"


# Scenario: A published non-v2 row fails closed with the uniform 404
@pytest.mark.asyncio
async def test_published_non_v2_row_fails_closed_with_404() -> None:
    legacy: dict[str, object] = {"markdown": "## A\n\nCorpo"}
    row = _published_row(legacy)

    with pytest.raises(HTTPException) as excinfo:
        await _handler()(
            request=None,
            post_id=UUID(POST_ID),
            db=_FakeDb(row),
        )

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == ERR_PUBLIC_BLOG_POST_NOT_FOUND
