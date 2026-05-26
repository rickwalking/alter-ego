"""Tests for Phase 1 new API endpoints."""

import os
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_AUTH
from rag_backend.domain.models import User, UserRole

TEST_SECRET = "test-secret-for-phase1-integration-tests!"


@pytest.fixture(autouse=True)
def _test_settings():
    """Override secret keys for all tests in this module."""
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-phase1-tests"
    yield
    get_settings.cache_clear()


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


@pytest.fixture
async def client():
    """Create async test client with in-memory SQLite and auth."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db_config.c_engine = engine

    admin = await _create_user("test@example.com", UserRole.ADMIN)

    app = create_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=_auth_headers(admin),
    ) as ac:
        yield ac

    db_config.c_engine = None
    await close_db()
    await engine.dispose()


class TestPersonaEndpoints:
    """Tests for persona management endpoints."""

    @pytest.mark.asyncio
    async def test_create_persona(self, client: AsyncClient):
        """Test creating a persona profile."""
        payload = {
            "name": "Test Persona",
            "description": "A test persona",
            "tone_attributes": {
                "formal": 0.3,
                "conversational": 0.8,
                "humorous": 0.4,
            },
            "writing_samples": ["Sample 1", "Sample 2"],
            "forbidden_phrases": ["bad phrase"],
            "preferred_phrases": ["good phrase"],
            "expertise_areas": ["AI", "testing"],
        }
        response = await client.post("/api/personas", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Persona"
        assert data["description"] == "A test persona"

    @pytest.mark.asyncio
    async def test_list_personas(self, client: AsyncClient):
        """Test listing persona profiles."""
        response = await client.get("/api/personas")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_persona(self, client: AsyncClient):
        """Test getting a specific persona profile."""
        # First create a persona
        create_payload = {"name": "Get Test", "description": "For get test"}
        create_response = await client.post("/api/personas", json=create_payload)
        created = create_response.json()

        # Then get it
        response = await client.get(f"/api/personas/{created['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Test"

    @pytest.mark.asyncio
    async def test_update_persona(self, client: AsyncClient):
        """Test updating a persona profile."""
        # First create a persona
        create_payload = {"name": "Update Test", "description": "Before update"}
        create_response = await client.post("/api/personas", json=create_payload)
        created = create_response.json()

        # Then update it
        update_payload = {"name": "Updated Name", "description": "After update"}
        response = await client.put(
            f"/api/personas/{created['id']}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "After update"

    @pytest.mark.asyncio
    async def test_delete_persona(self, client: AsyncClient):
        """Test deleting a persona profile."""
        # First create a persona
        create_payload = {"name": "Delete Test"}
        create_response = await client.post("/api/personas", json=create_payload)
        created = create_response.json()

        # Then delete it
        response = await client.delete(f"/api/personas/{created['id']}")
        assert response.status_code == 204


class TestRubricEndpoints:
    """Tests for rubric management endpoints."""

    @pytest.mark.asyncio
    async def test_create_rubric(self, client: AsyncClient):
        """Test creating a quality rubric."""
        payload = {
            "name": "Test Rubric",
            "description": "A test rubric",
            "criteria": [
                {
                    "id": "test_criterion",
                    "name": "Test Criterion",
                    "description": "For testing",
                    "weight": 0.5,
                    "evaluation_method": "ai_auto",
                    "min_threshold": 0.7,
                    "scoring_scale": "0-100",
                    "prompt_template": "Evaluate this",
                }
            ],
            "applicable_content_types": ["blog_post"],
            "is_default": False,
        }
        response = await client.post("/api/rubrics", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Rubric"

    @pytest.mark.asyncio
    async def test_list_rubrics(self, client: AsyncClient):
        """Test listing quality rubrics."""
        response = await client.get("/api/rubrics")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestBlogPostEndpoints:
    """Tests for blog post management endpoints."""

    @pytest.mark.asyncio
    async def test_create_blog_post(self, client: AsyncClient):
        """Test creating a blog post."""
        payload = {
            "title": "Test Blog Post",
            "slug": "test-blog-post",
            "content": {"blocks": []},
            "excerpt": "A test excerpt",
            "author_id": "test-author",
        }
        response = await client.post("/api/blog-posts", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Blog Post"
        assert data["slug"] == "test-blog-post"
        assert data["status"] == "draft"

    @pytest.mark.asyncio
    async def test_list_blog_posts(self, client: AsyncClient):
        """Test listing blog posts."""
        response = await client.get("/api/blog-posts")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_blog_post(self, client: AsyncClient):
        """Test getting a specific blog post."""
        # First create a blog post
        create_payload = {"title": "Get Test", "slug": "get-test"}
        create_response = await client.post("/api/blog-posts", json=create_payload)
        created = create_response.json()

        # Then get it
        response = await client.get(f"/api/blog-posts/{created['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Get Test"

    @pytest.mark.asyncio
    async def test_update_blog_post(self, client: AsyncClient):
        """Test updating a blog post."""
        # First create a blog post
        create_payload = {"title": "Update Test", "slug": "update-test"}
        create_response = await client.post("/api/blog-posts", json=create_payload)
        created = create_response.json()

        # Then update it with optimistic locking
        update_payload = {"title": "Updated Title"}
        response = await client.put(
            f"/api/blog-posts/{created['id']}",
            json=update_payload,
            headers={"If-Match": str(created.get("lock_version", 1))},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_blog_post_requires_if_match(self, client: AsyncClient):
        """Test that blog post update requires If-Match header."""
        create_payload = {"title": "Lock Test", "slug": "lock-test"}
        create_response = await client.post("/api/blog-posts", json=create_payload)
        created = create_response.json()

        response = await client.put(
            f"/api/blog-posts/{created['id']}",
            json={"title": "No Header"},
        )
        assert response.status_code == 428

    @pytest.mark.asyncio
    async def test_update_blog_post_rejects_status_change(self, client: AsyncClient):
        """Non-admin cannot bypass workflow by setting status on PUT."""
        create_payload = {"title": "Status Bypass Test", "slug": "status-bypass-test"}
        create_response = await client.post("/api/blog-posts", json=create_payload)
        created = create_response.json()

        response = await client.put(
            f"/api/blog-posts/{created['id']}",
            json={"status": "published"},
            headers={"If-Match": str(created.get("lock_version", 1))},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "workflow_field_immutable"

    @pytest.mark.asyncio
    async def test_update_blog_post_rejects_status_change_for_admin(
        self, client: AsyncClient
    ):
        """Admin cannot bypass workflow by setting status on PUT."""
        create_payload = {"title": "Admin Status Bypass", "slug": "admin-status-bypass"}
        create_response = await client.post("/api/blog-posts", json=create_payload)
        created = create_response.json()

        response = await client.put(
            f"/api/blog-posts/{created['id']}",
            json={"status": "published"},
            headers={"If-Match": str(created.get("lock_version", 1))},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "workflow_field_immutable"

    @pytest.mark.asyncio
    async def test_update_blog_post_version_conflict(self, client: AsyncClient):
        """Stale If-Match should return 409 version_conflict."""
        create_payload = {"title": "Conflict Test", "slug": "conflict-test"}
        create_response = await client.post("/api/blog-posts", json=create_payload)
        created = create_response.json()
        initial_version = created.get("lock_version", 1)

        first_update = await client.put(
            f"/api/blog-posts/{created['id']}",
            json={"title": "First Update"},
            headers={"If-Match": str(initial_version)},
        )
        assert first_update.status_code == 200

        response = await client.put(
            f"/api/blog-posts/{created['id']}",
            json={"title": "Stale Update"},
            headers={"If-Match": str(initial_version)},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_blog_post(self, client: AsyncClient):
        """Test deleting a blog post."""
        # First create a blog post
        create_payload = {"title": "Delete Test", "slug": "delete-test"}
        create_response = await client.post("/api/blog-posts", json=create_payload)
        created = create_response.json()

        # Then delete it
        response = await client.delete(f"/api/blog-posts/{created['id']}")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_blog_post_workflow(self, client: AsyncClient):
        """Test the full blog post workflow."""
        reviewer = await _create_user("reviewer@example.com", UserRole.EDITOR)

        # Create a blog post owned by admin
        create_payload = {
            "title": "Workflow Test",
            "slug": "workflow-test",
        }
        create_response = await client.post("/api/blog-posts", json=create_payload)
        post = create_response.json()

        # Submit for review with explicit reviewer (not the author)
        review_response = await client.post(
            f"/api/blog-posts/{post['id']}/submit-review?reviewer_id={reviewer.id}",
        )
        assert review_response.status_code == 200
        reviewed = review_response.json()
        assert reviewed["status"] == "under_review"

        # Approve as admin (assigned reviewer or admin)
        approve_response = await client.post(f"/api/blog-posts/{post['id']}/approve")
        assert approve_response.status_code == 200
        approved = approve_response.json()
        assert approved["status"] == "approved"

        # Publish
        publish_response = await client.post(f"/api/blog-posts/{post['id']}/publish")
        assert publish_response.status_code == 200
        published = publish_response.json()
        assert published["status"] == "published"


class TestSourceEndpoints:
    """Tests for content source management endpoints."""

    @pytest.mark.asyncio
    async def test_list_sources_for_project(self, client: AsyncClient):
        """Test listing sources for a project."""
        create_response = await client.post(
            "/api/carousels",
            json={"topic": "T", "audience": "A", "niche": "N"},
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        response = await client.get(f"/api/projects/{project_id}/sources")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
