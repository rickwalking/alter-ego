"""Editor-read handler tests (AE-0428): strict read + standard 422 mapping.

Covers ``get_blog_post`` at the handler level (no HTTP transport) so the
removed read fail-safe is proven on the exact lines the AE-0428 diff changes:
a valid v2 row returns its parsed content and a non-v2 row fails closed.

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

import rag_backend.api.routes.blog_post as blog_post_routes
from rag_backend.api.schemas.blog_post import BlogPostResponse
from rag_backend.domain.constants.blog_document import ERR_BLOG_DOCUMENT_NOT_V2
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from tests.blog_v2_support import v2_content

POST_ID = "550e8400-e29b-41d4-a716-446655440000"

GetBlogPostHandler = Callable[..., Awaitable[BlogPostResponse]]


def _row(content: dict[str, object]) -> BlogPostModel:
    return BlogPostModel(
        id=POST_ID,
        project_id=None,
        origin="standalone",
        title="T",
        slug="t",
        status="draft",
        content=content,
        author_id="550e8400-e29b-41d4-a716-446655440001",
        editor_comments=[],
        sources=[],
        citations=[],
        ai_suggestions=[],
        ai_generation_metadata={},
        keywords=[],
        view_count=0,
        like_count=0,
        comment_count=0,
        share_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        lock_version=1,
    )


def _handler() -> GetBlogPostHandler:
    """The route function itself (slowapi wraps it; unwrap for a direct call)."""
    return cast(
        GetBlogPostHandler,
        inspect.unwrap(blog_post_routes.get_blog_post),
    )


# Scenario: A valid v2 read returns the parsed document content
@pytest.mark.asyncio
async def test_valid_v2_row_returns_parsed_content(monkeypatch) -> None:
    row = _row(v2_content("Corpo"))
    monkeypatch.setattr(
        blog_post_routes,
        "get_blog_post_for_read",
        lambda db, post_id, user: _return(row),
    )

    result = await _handler()(
        request=None,
        post_id=UUID(POST_ID),
        db=None,
        current_user=None,
    )

    assert result.id == UUID(POST_ID)
    assert result.content["schema"] == "blog.v2"
    assert result.content["sections"][0]["body_md"] == "Corpo"


async def _return(row: BlogPostModel) -> BlogPostModel:
    return row


# Scenario: A non-v2 editor read fails closed with the document error
@pytest.mark.asyncio
async def test_non_v2_row_fails_closed_with_422(monkeypatch) -> None:
    legacy: dict[str, object] = {"markdown": "## A\n\nCorpo"}
    row = _row(legacy)
    monkeypatch.setattr(
        blog_post_routes,
        "get_blog_post_for_read",
        lambda db, post_id, user: _return(row),
    )

    with pytest.raises(HTTPException) as excinfo:
        await _handler()(
            request=None,
            post_id=UUID(POST_ID),
            db=None,
            current_user=None,
        )

    assert excinfo.value.status_code == 422
    assert excinfo.value.detail == ERR_BLOG_DOCUMENT_NOT_V2
