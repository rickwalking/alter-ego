"""The public blog feed excludes draft, hidden and scheduled posts.

Feature: public_blog_unreleased_ae0449.feature
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from rag_backend.domain.constants.blog_post import BlogPostOrigin, BlogPostStatus
from rag_backend.domain.constants.blog_rebuild import HIDDEN_BAD_POST_KEY
from tests.blog_v2_support import v2_content

PUBLIC_LIST_URL = "/api/public/blog-posts"
HIDDEN_MARKER = {HIDDEN_BAD_POST_KEY: {"hidden_at": "2026-10-20T10:00:00+00:00"}}


@dataclass(frozen=True)
class PostFixture:
    """One carousel-origin blog row under a public carousel."""

    status: BlogPostStatus
    published_at: datetime | None = None
    scheduled_publish_at: datetime | None = None
    metadata: dict[str, dict[str, str]] = field(default_factory=dict)


async def _insert_public_carousel_post(fixture: PostFixture) -> str:
    """Insert a public carousel and its blog row; return the post id."""
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    project_id = str(uuid4())
    post_id = str(uuid4())
    async with get_session_maker()() as session:
        session.add(
            CarouselProjectModel(
                id=project_id,
                owner_id=None,
                topic="Fixture topic",
                audience="Fixture audience",
                niche="Fixture niche",
                is_public=True,
            )
        )
        session.add(
            BlogPostModel(
                id=post_id,
                title=f"Post {fixture.status.value}",
                slug=f"slug-{post_id}",
                status=fixture.status.value,
                origin=BlogPostOrigin.CAROUSEL.value,
                project_id=project_id,
                content=v2_content("Body"),
                ai_generation_metadata=fixture.metadata,
                published_at=fixture.published_at,
                scheduled_publish_at=fixture.scheduled_publish_at,
            )
        )
        await session.commit()
    return post_id


def _hidden_post() -> PostFixture:
    return PostFixture(status=BlogPostStatus.DRAFT, metadata=HIDDEN_MARKER)


def _scheduled_post() -> PostFixture:
    return PostFixture(
        status=BlogPostStatus.APPROVED,
        scheduled_publish_at=datetime.now(UTC) + timedelta(days=3),
    )


class TestPublicFeedExcludesUnreleased:
    # Scenario: Public list excludes draft, hidden and scheduled posts
    @pytest.mark.asyncio
    async def test_list_returns_only_the_published_post(
        self, client: AsyncClient
    ) -> None:
        published = await _insert_public_carousel_post(
            PostFixture(status=BlogPostStatus.PUBLISHED, published_at=datetime.now(UTC))
        )
        for unreleased in (
            PostFixture(status=BlogPostStatus.DRAFT),
            _hidden_post(),
            _scheduled_post(),
        ):
            await _insert_public_carousel_post(unreleased)

        response = await client.get(PUBLIC_LIST_URL)

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert [item["id"] for item in body["items"]] == [published]

    # Scenario: Hidden and scheduled posts are a uniform 404
    @pytest.mark.asyncio
    @pytest.mark.parametrize("make_fixture", [_hidden_post, _scheduled_post])
    async def test_unreleased_detail_is_404(
        self, client: AsyncClient, make_fixture: Callable[[], PostFixture]
    ) -> None:
        post_id = await _insert_public_carousel_post(make_fixture())

        response = await client.get(f"{PUBLIC_LIST_URL}/{post_id}")

        assert response.status_code == 404
