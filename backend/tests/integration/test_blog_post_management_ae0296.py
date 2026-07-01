"""Integration tests for blog post delete/unpublish guards (AE-0296).

Feature: blog_post_management_ae0296.feature
"""

import os
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_AUTH
from rag_backend.domain.constants.blog_post import (
    ERR_CAROUSEL_ORIGIN_DELETE_BLOCKED,
    BlogPostOrigin,
    BlogPostStatus,
)
from rag_backend.domain.constants.optimistic_locking import (
    ERR_VERSION_CONFLICT,
    HTTP_HEADER_IF_MATCH,
)
from rag_backend.domain.models import User, UserRole

TEST_SECRET = "test-secret-for-ae0296-management-tests"


@pytest.fixture(autouse=True)
def _test_settings():
    """Override secret keys for all tests in this module."""
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-ae0296-tests"
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client():
    """Create async test client with in-memory SQLite."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db_config.c_engine = engine

    app = create_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    db_config.c_engine = None
    await close_db()
    await engine.dispose()


async def _create_user(email: str, role: UserRole) -> User:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = PostgresUserRepository(session)
        user = User(
            email=email,
            full_name=email.split("@")[0].title(),
            role=role,
            hashed_password="not-used-in-tests",
        )
        created = await repo.create(user)
        await session.commit()
        return created


def _token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "type": JWT_TYPE_AUTH,
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm=JWT_ALGORITHM)


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user)}"}


async def _create_blog_post(
    client: AsyncClient, user: User, slug: str
) -> dict[str, object]:
    response = await client.post(
        "/api/blog-posts",
        json={"title": f"Post {slug}", "slug": slug},
        headers=_auth_headers(user),
    )
    assert response.status_code == 201
    return response.json()


async def _set_post_fields(post_id: str, **fields: object) -> None:
    """Directly mutate a blog row (test-only status/origin arrangement)."""
    from sqlalchemy import update

    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

    session_maker = get_session_maker()
    async with session_maker() as session:
        await session.execute(
            update(BlogPostModel).where(BlogPostModel.id == post_id).values(**fields)
        )
        await session.commit()


class TestDeleteGuards:
    """Feature: delete requires If-Match and respects the origin policy."""

    @pytest.mark.asyncio
    async def test_delete_without_if_match_is_428(self, client: AsyncClient) -> None:
        admin = await _create_user("admin-d1@example.com", UserRole.ADMIN)
        post = await _create_blog_post(client, admin, "del-needs-if-match")

        response = await client.delete(
            f"/api/blog-posts/{post['id']}", headers=_auth_headers(admin)
        )
        assert response.status_code == 428

        still_there = await client.get(
            f"/api/blog-posts/{post['id']}", headers=_auth_headers(admin)
        )
        assert still_there.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_standalone_with_current_version(
        self, client: AsyncClient
    ) -> None:
        admin = await _create_user("admin-d2@example.com", UserRole.ADMIN)
        post = await _create_blog_post(client, admin, "del-ok")

        response = await client.delete(
            f"/api/blog-posts/{post['id']}",
            headers={
                **_auth_headers(admin),
                HTTP_HEADER_IF_MATCH: str(post["lock_version"]),
            },
        )
        assert response.status_code == 204

        gone = await client.get(
            f"/api/blog-posts/{post['id']}", headers=_auth_headers(admin)
        )
        assert gone.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_with_stale_version_is_409(self, client: AsyncClient) -> None:
        admin = await _create_user("admin-d3@example.com", UserRole.ADMIN)
        post = await _create_blog_post(client, admin, "del-stale")
        await _set_post_fields(post["id"], lock_version=2)

        response = await client.delete(
            f"/api/blog-posts/{post['id']}",
            headers={**_auth_headers(admin), HTTP_HEADER_IF_MATCH: "1"},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == ERR_VERSION_CONFLICT

    @pytest.mark.asyncio
    async def test_delete_linked_carousel_origin_is_blocked(
        self, client: AsyncClient
    ) -> None:
        admin = await _create_user("admin-d4@example.com", UserRole.ADMIN)
        post = await _create_blog_post(client, admin, "del-carousel-linked")
        await _set_post_fields(
            post["id"],
            origin=BlogPostOrigin.CAROUSEL.value,
            project_id="11111111-1111-1111-1111-111111111111",
        )

        response = await client.delete(
            f"/api/blog-posts/{post['id']}",
            headers={
                **_auth_headers(admin),
                HTTP_HEADER_IF_MATCH: str(post["lock_version"]),
            },
        )
        assert response.status_code == 409
        assert response.json()["detail"] == ERR_CAROUSEL_ORIGIN_DELETE_BLOCKED

        still_there = await client.get(
            f"/api/blog-posts/{post['id']}", headers=_auth_headers(admin)
        )
        assert still_there.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_detached_carousel_origin_is_allowed(
        self, client: AsyncClient
    ) -> None:
        admin = await _create_user("admin-d5@example.com", UserRole.ADMIN)
        post = await _create_blog_post(client, admin, "del-carousel-detached")
        await _set_post_fields(
            post["id"], origin=BlogPostOrigin.CAROUSEL.value, project_id=None
        )

        response = await client.delete(
            f"/api/blog-posts/{post['id']}",
            headers={
                **_auth_headers(admin),
                HTTP_HEADER_IF_MATCH: str(post["lock_version"]),
            },
        )
        assert response.status_code == 204


class TestUnpublishGuards:
    """Feature: unpublish is an optimistic-locked visibility flip."""

    @pytest.mark.asyncio
    async def test_unpublish_without_if_match_is_428(self, client: AsyncClient) -> None:
        admin = await _create_user("admin-u1@example.com", UserRole.ADMIN)
        post = await _create_blog_post(client, admin, "unpub-needs-if-match")
        await _set_post_fields(post["id"], status=BlogPostStatus.PUBLISHED.value)

        response = await client.post(
            f"/api/blog-posts/{post['id']}/unpublish", headers=_auth_headers(admin)
        )
        assert response.status_code == 428

    @pytest.mark.asyncio
    async def test_unpublish_flips_to_draft_and_bumps_version(
        self, client: AsyncClient
    ) -> None:
        admin = await _create_user("admin-u2@example.com", UserRole.ADMIN)
        post = await _create_blog_post(client, admin, "unpub-ok")
        await _set_post_fields(
            post["id"],
            status=BlogPostStatus.PUBLISHED.value,
            published_at=datetime.now(UTC),
        )

        response = await client.post(
            f"/api/blog-posts/{post['id']}/unpublish",
            headers={
                **_auth_headers(admin),
                HTTP_HEADER_IF_MATCH: str(post["lock_version"]),
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == BlogPostStatus.DRAFT.value
        assert body["published_at"] is None
        assert body["lock_version"] == int(str(post["lock_version"])) + 1

    @pytest.mark.asyncio
    async def test_unpublish_with_stale_version_is_409(
        self, client: AsyncClient
    ) -> None:
        admin = await _create_user("admin-u3@example.com", UserRole.ADMIN)
        post = await _create_blog_post(client, admin, "unpub-stale")
        await _set_post_fields(
            post["id"], status=BlogPostStatus.PUBLISHED.value, lock_version=2
        )

        response = await client.post(
            f"/api/blog-posts/{post['id']}/unpublish",
            headers={**_auth_headers(admin), HTTP_HEADER_IF_MATCH: "1"},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == ERR_VERSION_CONFLICT

        listing = await client.get(
            f"/api/blog-posts/{post['id']}", headers=_auth_headers(admin)
        )
        assert listing.json()["status"] == BlogPostStatus.PUBLISHED.value

    @pytest.mark.asyncio
    async def test_summary_response_exposes_origin(self, client: AsyncClient) -> None:
        admin = await _create_user("admin-u4@example.com", UserRole.ADMIN)
        await _create_blog_post(client, admin, "origin-exposed")

        response = await client.get("/api/blog-posts", headers=_auth_headers(admin))
        assert response.status_code == 200
        items = response.json()["items"]
        assert items
        assert items[0]["origin"] == BlogPostOrigin.STANDALONE.value
