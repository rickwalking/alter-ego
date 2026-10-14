"""Story row, Story media source, and the public Story image route (AE-0369).

Gherkin: tests/features/autopilot_story_and_music.feature
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.routes.carousels import story_image as story_route
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.domain.publish import StoredContainer
from rag_backend.modules.autopilot.domain.story import (
    SaveStoryContainer,
    SaveStoryResult,
)
from rag_backend.modules.autopilot.infrastructure.story_media import (
    PublishingStoryMedia,
)
from rag_backend.modules.autopilot.infrastructure.story_store import SqlStoryStore
from rag_backend.modules.publishing.application.story_image import (
    render_story_image,
    story_paths,
)

_AT = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
_BASE = "https://api.test"


def _slide(output: Path) -> None:
    (output / "pt").mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1080, 1350), (10, 120, 200)).save(output / "pt" / "slide_1.jpg")


async def _carousel(session: AsyncSession, output_dir: str | None) -> str:
    project_id = str(uuid.uuid4())
    session.add(
        CarouselProjectModel(
            id=project_id,
            topic="topic",
            audience="devs",
            niche="Cibersegurança",
            image_style="neo_anime",
            output_dir=output_dir,
        )
    )
    await session.commit()
    return project_id


@pytest.mark.unit
class TestSqlStoryStore:
    """The one-row-per-carousel Story ledger."""

    async def test_container_then_result(self, db_session: AsyncSession) -> None:
        project_id = await _carousel(db_session, None)
        store = SqlStoryStore(db_session)
        assert await store.get(project_id) is None

        container = StoredContainer(container_id="story-c-1", created_at=_AT)
        await store.save_container(
            SaveStoryContainer(project_id=project_id, container=container)
        )
        pending = await store.get(project_id)
        assert pending is not None
        assert pending.state == "pending"
        assert pending.container == container

        await store.save_result(
            SaveStoryResult(
                project_id=project_id,
                state="published",
                media_id="story-m-1",
                error=None,
                at=_AT,
            )
        )
        done = await store.get(project_id)
        assert done is not None
        assert done.state == "published"
        assert done.media_id == "story-m-1"
        assert done.container == container

    async def test_failure_without_a_container(self, db_session: AsyncSession) -> None:
        project_id = await _carousel(db_session, None)
        store = SqlStoryStore(db_session)

        await store.save_result(
            SaveStoryResult(
                project_id=project_id,
                state="failed",
                media_id=None,
                error="story_image_missing",
                at=_AT,
            )
        )

        record = await store.get(project_id)
        assert record is not None
        assert record.container is None
        assert record.error == "story_image_missing"

    async def test_null_media_id_keeps_the_stored_one(
        self, db_session: AsyncSession
    ) -> None:
        project_id = await _carousel(db_session, None)
        store = SqlStoryStore(db_session)
        for media_id in ("story-m-1", None):
            await store.save_result(
                SaveStoryResult(
                    project_id=project_id,
                    state="published",
                    media_id=media_id,
                    error=None,
                    at=_AT,
                )
            )
        record = await store.get(project_id)
        assert record is not None and record.media_id == "story-m-1"


@pytest.mark.unit
class TestPublishingStoryMedia:
    """Scenario: No slide 1 means no Story image."""

    async def test_rendered_image_gets_a_public_url(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        _slide(tmp_path)
        project_id = await _carousel(db_session, str(tmp_path))

        media = await PublishingStoryMedia(db_session, _BASE).load(project_id)

        assert media is not None
        assert (
            media.image_url == f"{_BASE}/api/carousels/{project_id}/story-image/pt.jpg"
        )
        assert media.niche == "Cibersegurança"
        assert media.image_style == "neo_anime"
        assert (tmp_path / "story_pt.jpg").is_file()

    async def test_no_slide_means_no_url(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        project_id = await _carousel(db_session, str(tmp_path))
        media = await PublishingStoryMedia(db_session, _BASE).load(project_id)
        assert media is not None and media.image_url is None

    async def test_no_output_dir_means_no_url(self, db_session: AsyncSession) -> None:
        project_id = await _carousel(db_session, None)
        media = await PublishingStoryMedia(db_session, _BASE).load(project_id)
        assert media is not None and media.image_url is None

    async def test_no_public_base_url_means_no_url(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        _slide(tmp_path)
        project_id = await _carousel(db_session, str(tmp_path))
        media = await PublishingStoryMedia(db_session, "").load(project_id)
        assert media is not None and media.image_url is None

    async def test_unreadable_slide_means_no_url(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        (tmp_path / "pt").mkdir()
        (tmp_path / "pt" / "slide_1.jpg").write_bytes(b"not a jpeg")
        project_id = await _carousel(db_session, str(tmp_path))
        media = await PublishingStoryMedia(db_session, _BASE).load(project_id)
        assert media is not None and media.image_url is None

    async def test_unknown_carousel(self, db_session: AsyncSession) -> None:
        media = await PublishingStoryMedia(db_session, _BASE).load(str(uuid.uuid4()))
        assert media is None


@dataclass
class _Project:
    is_public: bool
    output_dir: str | None
    artifact_version: str | None = None


class _Handlers:
    def __init__(self, project: _Project | None) -> None:
        self._project = project

    async def get_project(self, project_id: UUID) -> _Project | None:
        del project_id
        return self._project


def _client(project: _Project | None) -> AsyncClient:
    app = FastAPI()
    app.include_router(story_route.router, prefix="/api/carousels")
    app.dependency_overrides[story_route.get_presentation_handlers] = lambda: _Handlers(
        project
    )
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _url() -> str:
    return f"/api/carousels/{uuid.uuid4()}/story-image/pt.jpg"


def _rendered(tmp_path: Path) -> str:
    _slide(tmp_path)
    paths = story_paths(str(tmp_path), None)
    assert paths is not None
    render_story_image(paths)
    return str(tmp_path)


@pytest.mark.unit
class TestStoryImageRoute:
    """Scenarios: the public Story image route and its gate."""

    async def test_public_carousel_is_served_without_auth(self, tmp_path: Path) -> None:
        project = _Project(is_public=True, output_dir=_rendered(tmp_path))
        async with _client(project) as client:
            response = await client.get(_url())
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert response.content == (tmp_path / "story_pt.jpg").read_bytes()

    async def test_private_carousel_is_404(self, tmp_path: Path) -> None:
        project = _Project(is_public=False, output_dir=_rendered(tmp_path))
        async with _client(project) as client:
            response = await client.get(_url())
        assert response.status_code == 404

    async def test_public_carousel_without_a_story_is_404(self, tmp_path: Path) -> None:
        project = _Project(is_public=True, output_dir=str(tmp_path))
        async with _client(project) as client:
            response = await client.get(_url())
        assert response.status_code == 404

    async def test_unknown_carousel_is_404(self) -> None:
        async with _client(None) as client:
            response = await client.get(_url())
        assert response.status_code == 404
