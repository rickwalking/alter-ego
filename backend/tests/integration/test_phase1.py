"""Tests for Phase 1 new API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.api.app import create_app
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.models import UserModel


@pytest.fixture
async def client():
    """Create async test client with in-memory SQLite and auth."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db_config.c_engine = engine

    # Create test user
    async with AsyncSession(engine) as session:
        user = UserModel(
            id="test-user-id",
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed-password",
            role=UserRole.ADMIN,
        )
        session.add(user)
        await session.commit()

    app = create_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        yield ac

    await close_db()


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
        response = await client.put(f"/api/personas/{created['id']}", json=update_payload)
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
        
        # Then update it
        update_payload = {"title": "Updated Title"}
        response = await client.put(f"/api/blog-posts/{created['id']}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

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
        # Create a blog post
        create_payload = {"title": "Workflow Test", "slug": "workflow-test"}
        create_response = await client.post("/api/blog-posts", json=create_payload)
        post = create_response.json()
        
        # Submit for review
        review_response = await client.post(f"/api/blog-posts/{post['id']}/submit-review")
        assert review_response.status_code == 200
        reviewed = review_response.json()
        assert reviewed["status"] == "under_review"
        
        # Approve
        approve_response = await client.post(
            f"/api/blog-posts/{post['id']}/approve?reviewer_id=test-reviewer"
        )
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
        # Using a dummy project ID
        response = await client.get("/api/projects/123e4567-e89b-12d3-a456-426614174000/sources")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
