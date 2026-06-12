"""Integration tests for the Instagram publish route.

Gherkin: tests/features/instagram_publisher.feature
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.api.constants import ERR_INSTAGRAM_PUBLIC_BASE_URL_NOT_CONFIGURED
from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_AUTH
from rag_backend.domain.constants.carousel_workflow import (
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.models import CarouselStatus, User, UserRole
from rag_backend.domain.protocols import PublishResult

TEST_SECRET = "test-secret-for-publish-api-integration-tests!"


@pytest.fixture(autouse=True)
def _test_settings():
    """Override secret keys for all tests in this module."""
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-publish-api-tests"
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
async def client_and_container():
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.container import get_container
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine

    editor = await _create_user("editor@example.com", UserRole.EDITOR)

    app = create_app()
    container = get_container()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=_auth_headers(editor),
    ) as ac:
        yield ac, container

    db_config.c_engine = None
    await close_db()
    await engine.dispose()


async def _seed_completed_project(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/carousels",
        json={"topic": "T", "audience": "A", "niche": "N"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Mark as COMPLETED directly in the repo — the full pipeline needs
    # real LLM + image SDKs we don't want to exercise here.
    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )

    assert db_config.c_engine is not None
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

    Session = async_sessionmaker(db_config.c_engine, expire_on_commit=False)
    async with Session() as session:
        repo = PostgresCarouselRepository(session)
        from uuid import UUID

        proj = await repo.get_project_by_id(UUID(project_id))
        assert proj is not None
        proj.status = CarouselStatus.COMPLETED
        proj.output_dir = "/tmp/test-carousel-output"
        await repo.update_project(proj)
        model = await session.get(CarouselProjectModel, project_id)
        if model is not None:
            model.workflow_status = WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
            await session.commit()

    # Create minimal artifacts so artifact health checks pass
    from tests.integration.carousel_consolidation.helpers import (
        create_minimal_carousel_artifacts,
    )

    await create_minimal_carousel_artifacts(project_id)
    return project_id


@pytest.mark.integration
class TestInstagramPublishRoute:
    """API-level coverage for /publish/instagram."""

    @pytest.mark.asyncio
    async def test_503_when_public_base_url_missing(
        self, client_and_container, monkeypatch
    ):
        client, container = client_and_container
        project_id = await _seed_completed_project(client)

        # Override publisher to one that would succeed so we isolate the URL check.
        fake = AsyncMock()
        fake.publish_instagram = AsyncMock(
            return_value=PublishResult(status="published", post_id="ignored"),
        )
        container.instagram_publisher.override(fake)

        monkeypatch.delenv("CAROUSEL_PUBLIC_BASE_URL", raising=False)
        from rag_backend.infrastructure.config.settings import get_settings

        get_settings.cache_clear()

        resp = await client.post(
            f"/api/carousels/{project_id}/publish/instagram",
            json={"caption": "hello"},
        )
        container.instagram_publisher.reset_override()
        assert resp.status_code == 503, resp.text
        assert ERR_INSTAGRAM_PUBLIC_BASE_URL_NOT_CONFIGURED in resp.text

    @pytest.mark.asyncio
    async def test_409_when_project_not_completed(self, client_and_container):
        client, _ = client_and_container
        resp = await client.post(
            "/api/carousels",
            json={"topic": "T", "audience": "A", "niche": "N"},
        )
        project_id = resp.json()["id"]

        from sqlalchemy.ext.asyncio import async_sessionmaker

        import rag_backend.infrastructure.database.config as db_config
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        assert db_config.c_engine is not None
        Session = async_sessionmaker(db_config.c_engine, expire_on_commit=False)
        async with Session() as session:
            model = await session.get(CarouselProjectModel, project_id)
            assert model is not None
            model.workflow_status = WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
            await session.commit()

        publish_resp = await client.post(
            f"/api/carousels/{project_id}/publish/instagram",
            json={"caption": "hello"},
        )
        assert publish_resp.status_code == 409

    @pytest.mark.asyncio
    async def test_404_when_project_missing(self, client_and_container):
        client, _ = client_and_container
        resp = await client.post(
            f"/api/carousels/{uuid4()}/publish/instagram",
            json={"caption": "hello"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_422_on_empty_caption(self, client_and_container):
        client, _ = client_and_container
        project_id = await _seed_completed_project(client)
        resp = await client.post(
            f"/api/carousels/{project_id}/publish/instagram",
            json={"caption": ""},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_happy_path_returns_published(
        self, client_and_container, monkeypatch
    ):
        client, container = client_and_container
        project_id = await _seed_completed_project(client)

        monkeypatch.setenv("CAROUSEL_PUBLIC_BASE_URL", "https://public.test")
        from rag_backend.infrastructure.config.settings import get_settings

        get_settings.cache_clear()

        fake = AsyncMock()
        fake.publish_instagram = AsyncMock(
            return_value=PublishResult(
                status="published",
                post_id="IG_17895_post",
            ),
        )
        container.instagram_publisher.override(fake)

        resp = await client.post(
            f"/api/carousels/{project_id}/publish/instagram",
            json={"caption": "my caption"},
        )
        container.instagram_publisher.reset_override()
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "published"
        assert body["ig_post_id"] == "IG_17895_post"

        # Publisher received URLs prefixed by the public base.
        call_args = fake.publish_instagram.call_args
        urls = call_args[0][1]
        assert all(url.startswith("https://public.test/") for url in urls)

    @pytest.mark.asyncio
    async def test_failure_bubbles_up_error_message(
        self, client_and_container, monkeypatch
    ):
        client, container = client_and_container
        project_id = await _seed_completed_project(client)

        monkeypatch.setenv("CAROUSEL_PUBLIC_BASE_URL", "https://public.test")
        from rag_backend.infrastructure.config.settings import get_settings

        get_settings.cache_clear()

        fake = AsyncMock()
        fake.publish_instagram = AsyncMock(
            return_value=PublishResult(
                status="failed",
                error_message="Meta token expired",
            ),
        )
        container.instagram_publisher.override(fake)

        resp = await client.post(
            f"/api/carousels/{project_id}/publish/instagram",
            json={"caption": "caption"},
        )
        container.instagram_publisher.reset_override()
        body = resp.json()
        assert body["status"] == "failed"
        assert body["error_message"] == "Meta token expired"
