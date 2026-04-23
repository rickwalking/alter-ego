"""Integration tests for carousel API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from rag_backend.api.app import create_app
from rag_backend.domain.models import CarouselProject, CarouselStatus


@pytest.fixture
async def client():
    """Create async test client with in-memory SQLite."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
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


@pytest.fixture
def mock_carousel_agent():
    """Create a mock carousel agent for pipeline tests."""
    agent = AsyncMock()
    project = CarouselProject(
        topic="Test Topic",
        audience="Test Audience",
        niche="Test Niche",
    )
    project.status = CarouselStatus.COMPLETED
    project.blog_markdown = "# Blog Post\n\nContent here."
    project.caption = "Great post! #ML #AI"
    agent.execute_pipeline.return_value = project
    return agent


@pytest.mark.integration
class TestCarouselEndpoints:
    """Integration tests for carousel API endpoints."""

    @pytest.mark.asyncio
    async def test_create_carousel(self, client):
        """Given valid carousel data, when POST /api/carousels, then returns 201."""
        payload = {
            "topic": "Machine Learning Basics",
            "audience": "Beginners",
            "niche": "AI Education",
        }
        response = await client.post("/api/carousels", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["topic"] == "Machine Learning Basics"
        assert data["status"] == "pending"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_carousel_with_options(self, client):
        """Given carousel with options, when POST, then returns configured project."""
        payload = {
            "topic": "Deep Learning",
            "audience": "Advanced",
            "niche": "AI",
            "theme": "cybersecurity",
        }
        response = await client.post("/api/carousels", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["theme"] == "cybersecurity"

    @pytest.mark.asyncio
    async def test_create_carousel_validation_error(self, client):
        """Given missing required fields, when POST, then returns 422."""
        payload = {"topic": "Test"}
        response = await client.post("/api/carousels", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_carousels_empty(self, client):
        """Given no carousels, when GET /api/carousels, then returns empty list."""
        response = await client.get("/api/carousels")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_carousels_with_data(self, client):
        """Given carousels exist, when GET, then returns list with items."""
        payload = {
            "topic": "Test Carousel",
            "audience": "Everyone",
            "niche": "Tech",
        }
        await client.post("/api/carousels", json=payload)

        response = await client.get("/api/carousels")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["topic"] == "Test Carousel"

    @pytest.mark.asyncio
    async def test_get_carousel_by_id(self, client):
        """Given carousel exists, when GET /api/carousels/{id}, then returns it."""
        payload = {
            "topic": "Get By ID Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_response = await client.post("/api/carousels", json=payload)
        carousel_id = create_response.json()["id"]

        response = await client.get(f"/api/carousels/{carousel_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == carousel_id
        assert data["topic"] == "Get By ID Test"

    @pytest.mark.asyncio
    async def test_get_carousel_not_found(self, client):
        """Given non-existent ID, when GET, then returns 404."""
        response = await client.get("/api/carousels/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_carousel_status(self, client):
        """Given carousel exists, when GET /api/carousels/{id}/status, then returns status."""
        payload = {
            "topic": "Status Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_response = await client.post("/api/carousels", json=payload)
        carousel_id = create_response.json()["id"]

        response = await client.get(f"/api/carousels/{carousel_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == carousel_id
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_carousel_status_not_found(self, client):
        """Given non-existent ID, when GET status, then returns 404."""
        response = await client.get("/api/carousels/00000000-0000-0000-0000-000000000000/status")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_carousel_blog_not_generated(self, client):
        """Given carousel without blog, when GET blog, then returns 404."""
        payload = {
            "topic": "Blog Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_response = await client.post("/api/carousels", json=payload)
        carousel_id = create_response.json()["id"]

        response = await client.get(f"/api/carousels/{carousel_id}/blog")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_carousel(self, client):
        """Given carousel exists, when DELETE, then returns 204 and removes it."""
        payload = {
            "topic": "Delete Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_response = await client.post("/api/carousels", json=payload)
        carousel_id = create_response.json()["id"]

        response = await client.delete(f"/api/carousels/{carousel_id}")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_carousel_not_found(self, client):
        """Given non-existent ID, when DELETE, then returns 404."""
        response = await client.delete("/api/carousels/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_carousel_with_mock(self, client, mock_carousel_agent):
        """Given carousel exists, when POST generate, then runs pipeline."""
        payload = {
            "topic": "Generate Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_response = await client.post("/api/carousels", json=payload)
        carousel_id = create_response.json()["id"]

        with patch("rag_backend.infrastructure.container.get_container") as mock_container:
            from rag_backend.infrastructure.container import Container

            test_container = Container()
            test_container.carousel_agent.override(mock_carousel_agent)
            mock_container.return_value = test_container

            response = await client.post(
                f"/api/carousels/{carousel_id}/generate",
                json={"sources": None},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_stream_carousel_with_mock(self, client, mock_carousel_agent):
        """Given carousel exists, when GET stream, then returns SSE events."""
        payload = {
            "topic": "Stream Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_response = await client.post("/api/carousels", json=payload)
        carousel_id = create_response.json()["id"]

        async def fake_stream(*args, **kwargs):
            yield {"node": "start", "status": "pending", "phase_progress": None}
            yield {"node": "end", "status": "completed", "phase_progress": None}

        mock_carousel_agent.stream_pipeline = fake_stream

        with patch("rag_backend.infrastructure.container.get_container") as mock_container:
            from rag_backend.infrastructure.container import Container

            test_container = Container()
            test_container.carousel_agent.override(mock_carousel_agent)
            mock_container.return_value = test_container

            response = await client.get(f"/api/carousels/{carousel_id}/stream")
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            text = response.text
            assert "start" in text
            assert "end" in text

    @pytest.mark.asyncio
    async def test_stream_carousel_rejects_post(self, client):
        """Given the stream endpoint, when POST is used, then returns 405.

        Mutation guard: EventSource in browsers is GET-only. If the route
        is accidentally changed back to @router.post, this test fails.
        """
        payload = {
            "topic": "Stream Method Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_response = await client.post("/api/carousels", json=payload)
        carousel_id = create_response.json()["id"]

        response = await client.post(f"/api/carousels/{carousel_id}/stream", json={})
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_stream_carousel_passes_null_seed_urls(self, client, mock_carousel_agent):
        """Given GET stream, when invoked, then seed_urls is None.

        Mutation guard: EventSource cannot send a body, so the route must
        not require one. If seed_urls is accidentally made required, the
        endpoint will break browser-based streaming.
        """
        payload = {
            "topic": "Stream Null Seeds Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_response = await client.post("/api/carousels", json=payload)
        carousel_id = create_response.json()["id"]

        captured_args: dict = {}

        async def capturing_stream(*args, **kwargs):
            captured_args["args"] = args
            captured_args["kwargs"] = kwargs
            yield {"node": "end", "status": "completed", "phase_progress": None}

        mock_carousel_agent.stream_pipeline = capturing_stream

        with patch("rag_backend.infrastructure.container.get_container") as mock_container:
            from rag_backend.infrastructure.container import Container

            test_container = Container()
            test_container.carousel_agent.override(mock_carousel_agent)
            mock_container.return_value = test_container

            response = await client.get(f"/api/carousels/{carousel_id}/stream")
            assert response.status_code == 200
            assert captured_args.get("kwargs", {}).get("seed_urls") is None

    @pytest.mark.asyncio
    async def test_stream_carousel_yields_error_event(self, client, mock_carousel_agent):
        """Given pipeline error, when GET stream, then yields error event and closes.

        Mutation guard: ensures the SSE stream passes through the error
        event emitted by stream_pipeline rather than silently dropping it.
        """
        payload = {
            "topic": "Stream Error Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_response = await client.post("/api/carousels", json=payload)
        carousel_id = create_response.json()["id"]

        async def error_stream(*args, **kwargs):
            yield {"node": "start", "status": "pending", "phase_progress": None}
            yield {"node": "error", "status": "failed", "error": "pipeline exploded"}

        mock_carousel_agent.stream_pipeline = error_stream

        with patch("rag_backend.infrastructure.container.get_container") as mock_container:
            from rag_backend.infrastructure.container import Container

            test_container = Container()
            test_container.carousel_agent.override(mock_carousel_agent)
            mock_container.return_value = test_container

            response = await client.get(f"/api/carousels/{carousel_id}/stream")
            assert response.status_code == 200
            text = response.text
            assert "start" in text
            assert "pipeline exploded" in text

    @pytest.mark.asyncio
    async def test_list_carousels_with_status_filter(self, client):
        """Given carousels with different statuses, when filtered, then returns matching."""
        payload = {
            "topic": "Filter Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        await client.post("/api/carousels", json=payload)

        response = await client.get("/api/carousels?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert all(item["status"] == "pending" for item in data["items"])

    @pytest.mark.asyncio
    async def test_list_carousels_pagination(self, client):
        """Given multiple carousels, when paginated, then returns correct page."""
        for i in range(3):
            await client.post(
                "/api/carousels",
                json={
                    "topic": f"Pagination Test {i}",
                    "audience": "Everyone",
                    "niche": "Tech",
                },
            )

        response = await client.get("/api/carousels?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_get_carousel_download_not_generated(self, client):
        """Given carousel without output, when GET download, then returns 404."""
        payload = {
            "topic": "Download Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_response = await client.post("/api/carousels", json=payload)
        carousel_id = create_response.json()["id"]

        response = await client.get(f"/api/carousels/{carousel_id}/download")
        assert response.status_code == 404
