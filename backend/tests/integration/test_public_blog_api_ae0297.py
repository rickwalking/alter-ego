"""Integration tests for the public blog-post read API (AE-0297, ADR-0013).

Feature: public_blog_api_ae0297.feature
"""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.api.schemas.public_blog_post import (
    PUBLIC_BLOG_POST_EXCLUDED_FIELDS,
)
from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_AUTH
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_PUBLIC_BLOG_READ
from rag_backend.domain.models import User, UserRole

TEST_SECRET = "test-secret-for-ae0297-public-blog-tests"

PUBLIC_LIST_URL = "/api/public/blog-posts"


@pytest.fixture(autouse=True)
def _test_settings():
    """Override secret keys for all tests in this module."""
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-ae0297-tests"
    yield
    get_settings.cache_clear()


@pytest.fixture
async def app_under_test():
    """Create the app wired to an in-memory SQLite engine."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db_config.c_engine = engine

    yield create_app()

    db_config.c_engine = None
    await close_db()
    await engine.dispose()


@pytest.fixture
async def client(app_under_test):
    """Async test client over the app under test."""
    transport = ASGITransport(app=app_under_test)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


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


def _auth_headers(user: User) -> dict[str, str]:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "type": JWT_TYPE_AUTH,
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(payload, TEST_SECRET, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


async def _insert_post(
    *,
    status_value: str,
    published_at: datetime | None = None,
    title: str = "Post",
) -> str:
    """Insert a blog row directly, rich in internal fields."""
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

    post_id = str(uuid4())
    session_maker = get_session_maker()
    async with session_maker() as session:
        session.add(
            BlogPostModel(
                id=post_id,
                title=title,
                slug=f"slug-{post_id}",
                status=status_value,
                content={"markdown": "# Body"},
                excerpt="Excerpt",
                author_id="author-1",
                reviewer_id="reviewer-1",
                editor_comments=["internal comment"],
                version_history=["v1"],
                ai_suggestions=[{"note": "internal"}],
                ai_generation_metadata={"model": "internal"},
                published_at=published_at,
            )
        )
        await session.commit()
    return post_id


def _all_keys(payload: object) -> set[str]:
    """Recursively collect every dict key in a JSON payload."""
    keys: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            keys.add(str(key))
            keys |= _all_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            keys |= _all_keys(item)
    return keys


class TestPublicList:
    @pytest.mark.asyncio
    async def test_list_returns_only_published_ordered_desc(
        self, client: AsyncClient
    ) -> None:
        now = datetime.now(UTC)
        old = await _insert_post(
            status_value=BlogPostStatus.PUBLISHED.value,
            published_at=now - timedelta(days=2),
            title="Older",
        )
        new = await _insert_post(
            status_value=BlogPostStatus.PUBLISHED.value,
            published_at=now,
            title="Newer",
        )
        for hidden in (
            BlogPostStatus.DRAFT,
            BlogPostStatus.UNDER_REVIEW,
            BlogPostStatus.APPROVED,
            BlogPostStatus.ARCHIVED,
        ):
            await _insert_post(status_value=hidden.value)

        response = await client.get(PUBLIC_LIST_URL)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert [item["id"] for item in body["items"]] == [new, old]

    @pytest.mark.asyncio
    async def test_list_ignores_client_status_filter(
        self, client: AsyncClient
    ) -> None:
        await _insert_post(status_value=BlogPostStatus.DRAFT.value)

        response = await client.get(f"{PUBLIC_LIST_URL}?status=draft")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_list_sets_no_store(self, client: AsyncClient) -> None:
        response = await client.get(PUBLIC_LIST_URL)
        assert response.headers["Cache-Control"] == "no-store"


class TestPublicDetail:
    @pytest.mark.asyncio
    async def test_published_post_is_publicly_readable(
        self, client: AsyncClient
    ) -> None:
        post_id = await _insert_post(
            status_value=BlogPostStatus.PUBLISHED.value,
            published_at=datetime.now(UTC),
        )
        response = await client.get(f"{PUBLIC_LIST_URL}/{post_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == post_id
        assert body["content"] == {"markdown": "# Body"}
        assert response.headers["Cache-Control"] == "no-store"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "hidden_status",
        [
            BlogPostStatus.DRAFT,
            BlogPostStatus.UNDER_REVIEW,
            BlogPostStatus.APPROVED,
            BlogPostStatus.ARCHIVED,
        ],
    )
    async def test_uniform_404_for_non_published(
        self, client: AsyncClient, hidden_status: BlogPostStatus
    ) -> None:
        post_id = await _insert_post(status_value=hidden_status.value)
        response = await client.get(f"{PUBLIC_LIST_URL}/{post_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_unknown_id_is_the_same_404(self, client: AsyncClient) -> None:
        response = await client.get(f"{PUBLIC_LIST_URL}/{uuid4()}")
        assert response.status_code == 404


class TestLeanSchemaSecurity:
    @pytest.mark.asyncio
    async def test_no_excluded_key_appears_recursively(
        self, client: AsyncClient
    ) -> None:
        post_id = await _insert_post(
            status_value=BlogPostStatus.PUBLISHED.value,
            published_at=datetime.now(UTC),
        )
        list_body = (await client.get(PUBLIC_LIST_URL)).json()
        detail_body = (await client.get(f"{PUBLIC_LIST_URL}/{post_id}")).json()

        leaked_list = _all_keys(list_body) & PUBLIC_BLOG_POST_EXCLUDED_FIELDS
        leaked_detail = _all_keys(detail_body) & PUBLIC_BLOG_POST_EXCLUDED_FIELDS
        assert not leaked_list, f"public list leaks: {leaked_list}"
        assert not leaked_detail, f"public detail leaks: {leaked_detail}"

    @pytest.mark.asyncio
    async def test_editor_gets_byte_identical_anonymous_payload(
        self, client: AsyncClient
    ) -> None:
        editor = await _create_user("editor-pub@example.com", UserRole.EDITOR)
        post_id = await _insert_post(
            status_value=BlogPostStatus.PUBLISHED.value,
            published_at=datetime.now(UTC),
        )
        anon = await client.get(f"{PUBLIC_LIST_URL}/{post_id}")
        authed = await client.get(
            f"{PUBLIC_LIST_URL}/{post_id}", headers=_auth_headers(editor)
        )
        assert anon.content == authed.content

        draft_id = await _insert_post(status_value=BlogPostStatus.DRAFT.value)
        own_draft = await client.get(
            f"{PUBLIC_LIST_URL}/{draft_id}", headers=_auth_headers(editor)
        )
        assert own_draft.status_code == 404


class TestStructuralGuards:
    @pytest.mark.asyncio
    async def test_public_routes_resolve_no_auth_dependency(
        self, app_under_test
    ) -> None:
        """The dependency tree must be auth-free (role-blind by construction)."""
        from fastapi.routing import APIRoute

        app = app_under_test

        def _walk(dependant) -> list[str]:
            names = []
            for dep in dependant.dependencies:
                if dep.call is not None:
                    names.append(f"{dep.call.__module__}.{dep.call.__qualname__}")
                names.extend(_walk(dep))
            return names

        public_routes = [
            route
            for route in app.routes
            if isinstance(route, APIRoute) and route.path.startswith(PUBLIC_LIST_URL)
        ]
        assert len(public_routes) == 2

        for route in public_routes:
            deps = _walk(route.dependant)
            offenders = [
                name
                for name in deps
                if "dependencies.auth" in name or "dependencies.roles" in name
            ]
            assert not offenders, f"{route.path} resolves auth deps: {offenders}"

    def test_committed_rate_limit_ceiling(self) -> None:
        rate, _, window = RATE_LIMIT_PUBLIC_BLOG_READ.partition("/")
        assert window == "minute"
        assert int(rate) <= 120

    @pytest.mark.asyncio
    async def test_private_surface_still_returns_drafts(
        self, client: AsyncClient
    ) -> None:
        admin = await _create_user("admin-pub@example.com", UserRole.ADMIN)
        await _insert_post(status_value=BlogPostStatus.DRAFT.value, title="Draft")

        response = await client.get("/api/blog-posts", headers=_auth_headers(admin))
        assert response.status_code == 200
        statuses = {item["status"] for item in response.json()["items"]}
        assert BlogPostStatus.DRAFT.value in statuses
