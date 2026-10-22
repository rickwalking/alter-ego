"""Public blog list filtered by carousel ``project_id``.

Feature: public_blog_project_filter_ae0461.feature
"""

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.constants.blog_post import BlogPostStatus
from tests.blog_v2_support import v2_content

PUBLIC_LIST_URL = "/api/public/blog-posts"
ORIGIN_CAROUSEL = "carousel"


@pytest.fixture(autouse=True)
def _test_settings():
    """Override secret keys for all tests in this module."""
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = "test-secret-for-ae0461-public-blog-filter"
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-ae0461"
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client():
    """App over an in-memory SQLite engine."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    db_config.c_engine = None
    await close_db()
    await engine.dispose()


async def _public_carousel() -> str:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    project_id = str(uuid4())
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
        await session.commit()
    return project_id


async def _carousel_post(project_id: str, status_value: str) -> str:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

    post_id = str(uuid4())
    async with get_session_maker()() as session:
        session.add(
            BlogPostModel(
                id=post_id,
                title="Post",
                slug=f"slug-{post_id}",
                status=status_value,
                origin=ORIGIN_CAROUSEL,
                project_id=project_id,
                content=v2_content("Body"),
                published_at=datetime.now(UTC),
            )
        )
        await session.commit()
    return post_id


@pytest.mark.asyncio
async def test_filter_returns_only_the_carousel_post(client: AsyncClient) -> None:
    # Scenario: The public list returns the published post of one carousel
    carousel_a = await _public_carousel()
    carousel_b = await _public_carousel()
    post_a = await _carousel_post(carousel_a, BlogPostStatus.PUBLISHED.value)
    await _carousel_post(carousel_b, BlogPostStatus.PUBLISHED.value)

    response = await client.get(PUBLIC_LIST_URL, params={"project_id": carousel_a})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [post_a]
    assert body["items"][0]["project_id"] == carousel_a


@pytest.mark.asyncio
async def test_unpublished_carousel_post_is_not_listed(client: AsyncClient) -> None:
    # Scenario: A carousel whose post is not published returns an empty list
    carousel_c = await _public_carousel()
    await _carousel_post(carousel_c, BlogPostStatus.DRAFT.value)

    response = await client.get(PUBLIC_LIST_URL, params={"project_id": carousel_c})

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


@pytest.mark.asyncio
async def test_unfiltered_list_still_lists_every_carousel(client: AsyncClient) -> None:
    # Scenario: The public list returns the published post of one carousel
    for _ in range(2):
        await _carousel_post(await _public_carousel(), BlogPostStatus.PUBLISHED.value)

    response = await client.get(PUBLIC_LIST_URL)

    assert response.json()["total"] == 2


@pytest.mark.asyncio
async def test_malformed_project_id_is_rejected(client: AsyncClient) -> None:
    # Scenario: A malformed carousel id is rejected
    response = await client.get(PUBLIC_LIST_URL, params={"project_id": "not-a-uuid"})

    assert response.status_code == 422
