"""Deleting a photo from the owner's private photo library.

Gherkin: tests/features/creator_photo_delete_ae0494.feature
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from structlog.testing import capture_logs

from rag_backend.domain.models import UserRole
from rag_backend.modules.autopilot.domain.cover import CoverAsset
from rag_backend.modules.autopilot.domain.cover_ports import CoverClaim
from rag_backend.modules.autopilot.domain.models import TopicCandidate
from rag_backend.modules.autopilot.infrastructure.cover_store import SqlCoverAssetStore
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from tests.integration.conftest import auth_headers_for, create_test_user
from tests.integration.hook_photo_support import upload_photo

_LIBRARY = "/api/carousels/creator-assets"
_UNKNOWN = "00000000-0000-4000-8000-000000000009"


@pytest.fixture(autouse=True)
def _fresh_limiter() -> Iterator[None]:
    """The in-memory limiter is process-wide; these tests upload a lot."""
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()
    yield
    limiter.reset()


def _pov(photo_id: object) -> dict[str, object]:
    return {
        "topic": "Agentes no trabalho",
        "audience": "Devs",
        "niche": "IA",
        "content_mode": "pov",
        "pov_thesis": "A IA escreve código. Quem decide ainda é você.",
        "hook_asset_id": photo_id,
    }


async def _listed_ids(client: AsyncClient) -> list[str]:
    body = (await client.get(f"{_LIBRARY}?role=hook")).json()
    return [item["id"] for item in body["items"]]


async def _stored_file(asset_dirs: Path, photo: dict[str, object]) -> Path:
    return asset_dirs / "assets" / f"{photo['content_sha256']}.webp"


async def _set_project_column(project_id: str, column: str, value: object) -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    async with get_session_maker()() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        setattr(model, column, value)
        await session.commit()


async def _set_asset_role(photo_id: object, role: str) -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel_creator_asset import (
        CarouselCreatorAssetModel,
    )

    async with get_session_maker()() as session:
        model = await session.get(CarouselCreatorAssetModel, str(photo_id))
        assert model is not None
        model.role = role
        await session.commit()


def _topic(title: str) -> TopicCandidate:
    return TopicCandidate(
        candidate_id=uuid4(),
        title=title,
        angle="a",
        why_viral="w",
        audience="devs",
        niche="ai",
        brief="b",
        sources=("https://example.com/a",),
        score=80,
        signal_hash=uuid4().hex,
        status="pending",
        content_mode="pov",
    )


async def _autopilot_cover(photo_id: object, topic_title: str | None) -> UUID | None:
    """A GrokBot cover row on the photo, claimed by a new topic when titled."""
    from rag_backend.infrastructure.database.config import get_session_maker

    cover = CoverAsset(
        asset_id=uuid4(),
        creator_asset_id=UUID(str(photo_id)),
        kind="photo",
        source_url=None,
        width=1080,
        height=1350,
        created_at=datetime(2026, 10, 23, tzinfo=UTC),
    )
    async with get_session_maker()() as session:
        store = SqlCoverAssetStore(session)
        await store.add_cover(cover)
        topic_id = None
        if topic_title is not None:
            topic = _topic(topic_title)
            await SqlAlchemyAutopilotRepository(session).add_topic(topic)
            topic_id = topic.candidate_id
            claim = CoverClaim(asset_id=cover.asset_id, topic_candidate_id=topic_id)
            assert await store.claim_cover(claim)
        await store.commit()
    return topic_id


async def _plain_project(client: AsyncClient) -> str:
    created = await client.post(
        "/api/carousels", json={"topic": "Radar", "audience": "Devs", "niche": "IA"}
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


@pytest.mark.integration
class TestDeleteUnusedPhoto:
    @pytest.mark.asyncio
    async def test_unused_photo_is_deleted_with_its_file(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: An unused photo is deleted with its file."""
        photo = await upload_photo(client, (1, 2, 3, 0))
        keep = await upload_photo(client, (4, 5, 6, 0))
        stored = await _stored_file(asset_dirs, photo)
        assert stored.is_file()

        response = await client.delete(f"{_LIBRARY}/{photo['id']}")

        assert response.status_code == 204
        assert await _listed_ids(client) == [keep["id"]]
        image = await client.get(f"{_LIBRARY}/{photo['id']}/image")
        assert image.status_code == 404
        assert not stored.exists()
        assert (await _stored_file(asset_dirs, keep)).is_file()

    @pytest.mark.asyncio
    async def test_a_file_shared_by_another_owner_is_kept(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: A file shared by another owner's row is kept."""
        other = await create_test_user("twin@integration.test", UserRole.EDITOR)
        headers = auth_headers_for(other)
        mine = await upload_photo(client, (7, 7, 7, 0))
        theirs = await upload_photo(client, (7, 7, 7, 0), headers)
        assert mine["content_sha256"] == theirs["content_sha256"]

        response = await client.delete(f"{_LIBRARY}/{mine['id']}")

        assert response.status_code == 204
        image = await client.get(f"{_LIBRARY}/{theirs['id']}/image", headers=headers)
        assert image.status_code == 200

    @pytest.mark.asyncio
    async def test_a_photo_whose_file_is_gone_is_still_deleted(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: An unused photo is deleted with its file."""
        photo = await upload_photo(client, (8, 1, 8, 0))
        (await _stored_file(asset_dirs, photo)).unlink()

        response = await client.delete(f"{_LIBRARY}/{photo['id']}")

        assert response.status_code == 204
        assert await _listed_ids(client) == []


@pytest.mark.integration
class TestDeletePhotoInUse:
    @pytest.mark.asyncio
    async def test_hook_photo_of_a_carousel_is_kept(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: A photo used by a carousel cannot be deleted."""
        photo = await upload_photo(client, (2, 2, 2, 0))
        created = await client.post("/api/carousels", json=_pov(photo["id"]))
        assert created.status_code == 201, created.text
        project_id = created.json()["id"]

        response = await client.delete(f"{_LIBRARY}/{photo['id']}")

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["code"] == "creator_asset_in_use"
        assert [c["id"] for c in detail["carousels"]] == [project_id]
        assert set(detail["carousels"][0]) == {"id", "title"}
        assert await _listed_ids(client) == [photo["id"]]
        assert (await _stored_file(asset_dirs, photo)).is_file()

    @pytest.mark.parametrize("column", ["slide_cover", "creator_asset_id"])
    @pytest.mark.asyncio
    async def test_cover_or_creator_asset_of_a_carousel_is_kept(
        self, client: AsyncClient, asset_dirs: Path, column: str
    ) -> None:
        """Scenario: A photo used as a slide-1 cover or creator asset cannot be deleted."""
        photo = await upload_photo(client, (3, 3, 3, 0))
        project_id = await _plain_project(client)
        value: object = str(photo["id"])
        if column == "slide_cover":
            value = {"asset_id": str(photo["id"]), "kind": "photo", "staged_path": "c"}
        await _set_project_column(project_id, column, value)

        response = await client.delete(f"{_LIBRARY}/{photo['id']}")

        assert response.status_code == 409
        carousels = response.json()["detail"]["carousels"]
        assert carousels == [{"id": project_id, "title": None}]
        del asset_dirs


@pytest.mark.integration
class TestDeleteAutopilotCover:
    @pytest.mark.asyncio
    async def test_a_photo_a_pending_topic_uses_as_cover_is_kept(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: A photo an autopilot topic uses as its cover cannot be deleted."""
        photo = await upload_photo(client, (5, 1, 5, 0))
        topic_id = await _autopilot_cover(photo["id"], "Agentes no trabalho")
        await _autopilot_cover(photo["id"], None)

        response = await client.delete(f"{_LIBRARY}/{photo['id']}")

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["carousels"] == []
        topics = {(topic["id"], topic["title"]) for topic in detail["topics"]}
        assert topics == {(str(topic_id), "Agentes no trabalho"), (None, None)}
        assert await _listed_ids(client) == [photo["id"]]
        assert (await _stored_file(asset_dirs, photo)).is_file()

    @pytest.mark.asyncio
    async def test_a_grokbot_cover_asset_is_refused(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: A GrokBot cover is not deleted from the photo library."""
        photo = await upload_photo(client, (6, 1, 6, 0))
        await _set_asset_role(photo["id"], "cover")

        response = await client.delete(f"{_LIBRARY}/{photo['id']}")

        assert response.status_code == 409
        assert response.json()["detail"] == "creator_asset_cover_managed"
        assert (await _stored_file(asset_dirs, photo)).is_file()


@pytest.mark.integration
class TestDeleteFileError:
    @pytest.mark.asyncio
    async def test_a_file_that_cannot_be_removed_still_deletes_the_photo(
        self,
        client: AsyncClient,
        asset_dirs: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Scenario: A stored file that cannot be removed is logged, not an error."""
        photo = await upload_photo(client, (9, 1, 9, 0))
        stored = await _stored_file(asset_dirs, photo)

        def _refuse(self: Path, missing_ok: bool = False) -> None:
            raise PermissionError(13, "denied", str(self))

        monkeypatch.setattr(Path, "unlink", _refuse)
        with capture_logs() as logs:
            response = await client.delete(f"{_LIBRARY}/{photo['id']}")
        monkeypatch.undo()

        assert response.status_code == 204
        assert await _listed_ids(client) == []
        assert stored.is_file()
        failures = [
            log
            for log in logs
            if log["event"] == "creator_asset_stale_file_unlink_failed"
        ]
        assert failures == [
            {
                "event": "creator_asset_stale_file_unlink_failed",
                "asset_id": photo["id"],
                "log_level": "warning",
            }
        ]


@pytest.mark.integration
class TestDeleteAccess:
    @pytest.mark.parametrize("role", [UserRole.EDITOR, UserRole.ADMIN])
    @pytest.mark.asyncio
    async def test_another_user_cannot_delete(
        self, client: AsyncClient, asset_dirs: Path, role: UserRole
    ) -> None:
        """Scenario: Another user cannot delete the photo."""
        photo = await upload_photo(client, (4, 4, 4, 0))
        intruder = await create_test_user(f"{role.value}-x@integration.test", role)

        response = await client.delete(
            f"{_LIBRARY}/{photo['id']}", headers=auth_headers_for(intruder)
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "creator_asset_not_found"
        assert await _listed_ids(client) == [photo["id"]]
        del asset_dirs

    @pytest.mark.asyncio
    async def test_unknown_photo_is_404(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: Deleting an unknown photo returns not found."""
        response = await client.delete(f"{_LIBRARY}/{_UNKNOWN}")
        assert response.status_code == 404
        assert response.json()["detail"] == "creator_asset_not_found"
        del asset_dirs
