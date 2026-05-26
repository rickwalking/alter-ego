"""Integration tests for Phase 3 workflow collaboration APIs.

Feature: phase3_workflow_collaboration.feature
"""

import os
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_AUTH
from rag_backend.domain.constants.workflow_validation import (
    CONTENT_TYPE_BLOG_POST,
    CONTENT_TYPE_CAROUSEL,
)
from rag_backend.domain.models import User, UserRole

TEST_SECRET = "test-secret-for-phase3-workflow-tests!!"


@pytest.fixture(autouse=True)
def _test_settings():
    """Override secret keys for all tests in this module."""
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-phase3-tests"
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


class TestPhase3ReviewAssignment:
    """Feature: In-app notifications — assign reviewer to blog post."""

    @pytest.mark.asyncio
    async def test_reviewer_can_read_assigned_blog_post(
        self, client: AsyncClient
    ) -> None:
        """Assigned reviewer should read blog posts they do not own."""
        author = await _create_user("author@example.com", UserRole.EDITOR)
        reviewer = await _create_user("reviewer@example.com", UserRole.EDITOR)
        post = await _create_blog_post(client, author, "reviewer-read-test")

        assign_response = await client.post(
            "/api/notifications/assign-review",
            json={
                "reviewer_id": str(reviewer.id),
                "content_id": post["id"],
                "content_type": CONTENT_TYPE_BLOG_POST,
                "title": post["title"],
            },
            headers=_auth_headers(author),
        )
        assert assign_response.status_code == 200

        get_response = await client.get(
            f"/api/blog-posts/{post['id']}",
            headers=_auth_headers(reviewer),
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == post["id"]

    @pytest.mark.asyncio
    async def test_reviewer_cannot_reassign_review(self, client: AsyncClient) -> None:
        """Assigned reviewers must not reassign review to another user."""
        author = await _create_user("author2@example.com", UserRole.EDITOR)
        reviewer = await _create_user("reviewer2@example.com", UserRole.EDITOR)
        other = await _create_user("other@example.com", UserRole.EDITOR)
        post = await _create_blog_post(client, author, "reviewer-assign-deny")

        await client.post(
            "/api/notifications/assign-review",
            json={
                "reviewer_id": str(reviewer.id),
                "content_id": post["id"],
                "content_type": CONTENT_TYPE_BLOG_POST,
                "title": post["title"],
            },
            headers=_auth_headers(author),
        )

        response = await client.post(
            "/api/notifications/assign-review",
            json={
                "reviewer_id": str(other.id),
                "content_id": post["id"],
                "content_type": CONTENT_TYPE_BLOG_POST,
                "title": post["title"],
            },
            headers=_auth_headers(reviewer),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_carousel_assign_review_is_unsupported(
        self, client: AsyncClient
    ) -> None:
        """Carousel assign-review should fail before sending a notification."""
        author = await _create_user("carousel-author@example.com", UserRole.EDITOR)
        reviewer = await _create_user("carousel-reviewer@example.com", UserRole.EDITOR)

        create_response = await client.post(
            "/api/carousels",
            json={
                "topic": "Carousel Review",
                "audience": "Everyone",
                "niche": "Tech",
            },
            headers=_auth_headers(author),
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        response = await client.post(
            "/api/notifications/assign-review",
            json={
                "reviewer_id": str(reviewer.id),
                "content_id": project_id,
                "content_type": CONTENT_TYPE_CAROUSEL,
                "title": "Carousel review",
            },
            headers=_auth_headers(author),
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "reviewer_assignment_unsupported"


class TestPhase3WorkflowViews:
    """Feature: Content calendar and workflow Kanban board."""

    @pytest.mark.asyncio
    async def test_content_calendar_returns_items(self, client: AsyncClient) -> None:
        """Editors can load the content calendar."""
        user = await _create_user("calendar@example.com", UserRole.EDITOR)
        await _create_blog_post(client, user, "calendar-entry")

        response = await client.get(
            "/api/content-calendar", headers=_auth_headers(user)
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_workflow_board_returns_columns(self, client: AsyncClient) -> None:
        """Editors can load the workflow Kanban board."""
        user = await _create_user("kanban@example.com", UserRole.EDITOR)

        response = await client.get("/api/workflow-board", headers=_auth_headers(user))
        assert response.status_code == 200
        data = response.json()
        assert "columns" in data
