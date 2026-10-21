"""Integration tests for the blog dashboard fixes.

Feature: blog_dashboard_ae0411.feature

Content is a blog.v2 document (the only accepted write shape).
"""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.api.schemas.blog_post import BLOG_EXCERPT_MAX_LENGTH
from rag_backend.domain.constants.blog_post import (
    ERR_BLOG_POST_SLUG_CONFLICT,
    BlogPostOrigin,
    BlogPostStatus,
)
from rag_backend.domain.constants.optimistic_locking import HTTP_HEADER_IF_MATCH
from rag_backend.domain.models import UserRole
from tests.blog_v2_support import v2_content
from tests.integration.conftest import auth_headers_for, create_test_user

BLOG_POSTS_URL = "/api/blog-posts"
UNTITLED = "Untitled draft"
CAROUSEL_BODY = v2_content("Long body")


@pytest.fixture
async def admin_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    """Admin-authenticated client on a per-test SQLite file."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ae0411.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine

    admin = await create_test_user("admin@ae0411.test", UserRole.ADMIN)
    transport = ASGITransport(app=create_app())
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=auth_headers_for(admin)
    ) as ac:
        yield ac

    db_config.c_engine = None
    await close_db()
    await engine.dispose()


async def _create(client: AsyncClient, payload: dict[str, object]) -> dict[str, object]:
    response = await client.post(BLOG_POSTS_URL, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _insert_carousel_post(*, is_public: bool) -> str:
    """A carousel project + its dual-written ``published`` blog row."""
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    session_maker = get_session_maker()
    async with session_maker() as session:
        project = CarouselProjectModel(
            topic="T", audience="A", niche="N", is_public=is_public
        )
        session.add(project)
        await session.flush()
        post = BlogPostModel.from_entity({
            "project_id": str(project.id),
            "origin": BlogPostOrigin.CAROUSEL.value,
            "title": "Carousel post",
            "slug": f"carousel-{project.id}",
            "status": BlogPostStatus.PUBLISHED.value,
            "content": CAROUSEL_BODY,
        })
        session.add(post)
        await session.commit()
        return str(post.id)


async def _set_status(post_id: str, status: str) -> None:
    from sqlalchemy import update

    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

    session_maker = get_session_maker()
    async with session_maker() as session:
        await session.execute(
            update(BlogPostModel)
            .where(BlogPostModel.id == post_id)
            .values(status=status)
        )
        await session.commit()


async def _listed(client: AsyncClient, post_id: str) -> dict[str, object]:
    response = await client.get(BLOG_POSTS_URL)
    assert response.status_code == 200
    return next(item for item in response.json()["items"] if item["id"] == post_id)


class TestCreateSlug:
    """Feature: "New Post" never clashes on an empty slug."""

    @pytest.mark.asyncio
    async def test_two_posts_without_slug_get_distinct_slugs(
        self, admin_client: AsyncClient
    ) -> None:
        # Scenario: Creating two posts without a slug succeeds
        payload = {"title": UNTITLED, "content": v2_content(""), "excerpt": ""}
        first = await _create(admin_client, payload)
        second = await _create(admin_client, payload)
        assert first["slug"] != second["slug"]
        assert str(first["slug"]).startswith("untitled-draft-")
        assert str(second["slug"]).startswith("untitled-draft-")

    @pytest.mark.asyncio
    async def test_given_slug_is_kept(self, admin_client: AsyncClient) -> None:
        # Scenario: A given slug is kept
        post = await _create(admin_client, {"title": "Mine", "slug": "my-post"})
        assert post["slug"] == "my-post"

    @pytest.mark.asyncio
    async def test_duplicate_given_slug_is_clear_409(
        self, admin_client: AsyncClient
    ) -> None:
        # Scenario: A duplicate given slug is a clear 409
        await _create(admin_client, {"title": "One", "slug": "taken"})
        response = await admin_client.post(
            BLOG_POSTS_URL, json={"title": "Two", "slug": "taken"}
        )
        assert response.status_code == 409
        assert response.json()["detail"] == ERR_BLOG_POST_SLUG_CONFLICT

    @pytest.mark.asyncio
    async def test_blank_slug_is_generated(self, admin_client: AsyncClient) -> None:
        # Scenario: A blank slug is generated like a missing one
        post = await _create(admin_client, {"title": "Revisão humana!", "slug": "  "})
        assert str(post["slug"]).startswith("revisao-humana-")


class TestPartialUpdate:
    """Feature: a partial update leaves untouched fields as stored."""

    @pytest.mark.asyncio
    async def test_title_only_update_keeps_content(
        self, admin_client: AsyncClient
    ) -> None:
        # Scenario: A title-only update keeps the stored content
        post = await _create(admin_client, {"title": "Old", "content": CAROUSEL_BODY})
        response = await admin_client.put(
            f"{BLOG_POSTS_URL}/{post['id']}",
            json={"title": "New"},
            headers={HTTP_HEADER_IF_MATCH: str(post["lock_version"])},
        )
        assert response.status_code == 200
        detail = await admin_client.get(f"{BLOG_POSTS_URL}/{post['id']}")
        assert detail.json()["title"] == "New"
        assert detail.json()["content"] == CAROUSEL_BODY

    @pytest.mark.asyncio
    async def test_over_long_excerpt_is_422(self, admin_client: AsyncClient) -> None:
        # Scenario: An over-long excerpt is rejected as a validation error
        post = await _create(admin_client, {"title": "Post"})
        response = await admin_client.put(
            f"{BLOG_POSTS_URL}/{post['id']}",
            json={"excerpt": "x" * (BLOG_EXCERPT_MAX_LENGTH + 1)},
            headers={HTTP_HEADER_IF_MATCH: str(post["lock_version"])},
        )
        assert response.status_code == 422


class TestListLiveState:
    """Feature: the list says whether a post is really live."""

    @pytest.mark.asyncio
    async def test_standalone_published_is_public(
        self, admin_client: AsyncClient
    ) -> None:
        # Scenario: A standalone published post is live
        post = await _create(admin_client, {"title": "Live"})
        await _set_status(str(post["id"]), BlogPostStatus.PUBLISHED.value)
        assert (await _listed(admin_client, str(post["id"])))["is_public"] is True

    @pytest.mark.asyncio
    async def test_unreleased_carousel_post_is_not_public(
        self, admin_client: AsyncClient
    ) -> None:
        # Scenario: A carousel post whose carousel is not released is not live
        post_id = await _insert_carousel_post(is_public=False)
        item = await _listed(admin_client, post_id)
        assert item["status"] == BlogPostStatus.PUBLISHED.value
        assert item["is_public"] is False

    @pytest.mark.asyncio
    async def test_released_carousel_post_is_public(
        self, admin_client: AsyncClient
    ) -> None:
        # Scenario: A carousel post whose carousel is released is live
        post_id = await _insert_carousel_post(is_public=True)
        assert (await _listed(admin_client, post_id))["is_public"] is True

    @pytest.mark.asyncio
    async def test_draft_is_not_public(self, admin_client: AsyncClient) -> None:
        # Scenario: A draft is never live
        post = await _create(admin_client, {"title": "Draft"})
        assert (await _listed(admin_client, str(post["id"])))["is_public"] is False
