"""Grok cover generation from library photos over HTTP: start, store, pick, refuse.

Feature: Generate a slide-1 cover from library photos with Grok
(tests/features/cover_generation_ae0508.feature). The real app over an
in-memory SQLite database with a fake image bridge editor.
"""

from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image

from rag_backend.domain.models import UserRole
from tests.integration.conftest import auth_headers_for, create_test_user
from tests.integration.cover_generation_support import (
    BLUE,
    PROMPT,
    RED,
    FakeEditor,
    generate,
    generation_rows,
    install_fake_editor,
    install_renders,
    project,
    request_body,
    role_cover_assets,
    slide_cover,
)
from tests.integration.hook_photo_support import upload_photo


@pytest.fixture(autouse=True)
def _fresh_limiter() -> Iterator[None]:
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def editor(monkeypatch: pytest.MonkeyPatch) -> FakeEditor:
    return install_fake_editor(monkeypatch)


@pytest.fixture
def renders(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    return install_renders(monkeypatch)


@pytest.mark.integration
class TestGenerate:
    async def test_confirmed_generation_stores_a_private_cover(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: A confirmed generation sends the photo bytes and stores a private cover."""
        first = await upload_photo(client, RED)
        second = await upload_photo(client, BLUE)
        project_id = await project(client, first["id"])

        started = await generate(client, project_id, [first["id"], second["id"]])

        assert started["status"] == "pending"
        rows = await generation_rows(project_id)
        assert [row["photo_count"] for row in rows] == [2]
        job = editor.jobs[0]
        assert job.prompt == f"direction: {PROMPT}"
        assert job.project_id == project_id
        assert job.photo_count == 2
        assert str(job.job_id) == started["id"]
        assert rows[0]["photo_ids"] == [first["id"], second["id"]]
        listed = await client.get(f"/api/carousels/{project_id}/cover-generations")
        body = listed.json()
        assert body["carousel_used"] == 1
        assert body["carousel_cap"] == 4
        assert body["month_used"] == 1
        assert body["month_cap"] == 40
        generation = body["generations"][0]
        assert generation["status"] == "succeeded"
        assert generation["asset_id"] in await role_cover_assets()
        image = await client.get(
            f"/api/carousels/creator-assets/{generation['asset_id']}/image"
        )
        assert image.status_code == 200
        with Image.open(BytesIO(image.content)) as stored:
            assert stored.size == (1080, 1350)
        library = await client.get("/api/carousels/creator-assets?role=hook")
        library_ids = {item["id"] for item in library.json()["items"]}
        assert generation["asset_id"] not in library_ids

    async def test_generated_cover_is_an_option_and_can_be_picked(
        self,
        client: AsyncClient,
        asset_dirs: Path,
        editor: FakeEditor,
        renders: list[str],
    ) -> None:
        """Scenario: The generated cover is a cover option and can be picked."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])
        await generate(client, project_id, [photo["id"]])
        listed = await client.get(f"/api/carousels/{project_id}/cover-generations")
        asset_id = listed.json()["generations"][0]["asset_id"]

        options = await client.get(f"/api/carousels/{project_id}/cover-options")

        found = [
            (o["asset_id"], o["source"], o["kind"]) for o in options.json()["options"]
        ]
        assert found == [
            (photo["id"], "library", ""),
            (asset_id, "generated", "ai_image"),
        ]
        picked = await client.put(
            f"/api/carousels/{project_id}/cover",
            json={"asset_id": asset_id, "expected_version": 4},
        )
        assert picked.status_code == 200, picked.text
        assert picked.json()["current_asset_id"] == asset_id
        assert renders == [project_id]
        cover = await slide_cover(project_id)
        assert cover["asset_id"] == asset_id
        assert cover["kind"] == "ai_image"

    async def test_confirmation_is_required(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: Generation needs an explicit confirmation."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])

        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations",
            json=request_body([photo["id"]], confirmed=False),
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "cover_generation_not_confirmed"
        assert await generation_rows() == []
        assert editor.jobs == []

    async def test_only_the_owner_can_generate(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: Only the carousel's owner can generate."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])
        admin = await create_test_user(f"{uuid4().hex}@x.test", UserRole.ADMIN)

        posted = await client.post(
            f"/api/carousels/{project_id}/cover-generations",
            json=request_body([photo["id"]]),
            headers=auth_headers_for(admin),
        )
        listed = await client.get(
            f"/api/carousels/{project_id}/cover-generations",
            headers=auth_headers_for(admin),
        )

        assert posted.status_code == 403
        assert posted.json()["detail"] == "cover_generation_not_owner"
        assert listed.status_code == 403

    async def test_another_owners_photo_is_refused(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: Another owner's photo cannot be sent."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])
        other = await create_test_user(f"{uuid4().hex}@x.test", UserRole.EDITOR)
        theirs = await upload_photo(client, BLUE, headers=auth_headers_for(other))

        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations",
            json=request_body([theirs["id"]]),
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "cover_generation_photo_not_allowed"

    async def test_radar_carousel_is_refused(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: A Radar IA carousel cannot generate a cover."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, None, mode="news_analysis")

        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations",
            json=request_body([photo["id"]]),
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "cover_pick_not_pov"

    async def test_unknown_carousel_is_404(
        self, client: AsyncClient, editor: FakeEditor
    ) -> None:
        """Scenario: Only the carousel's owner can generate."""
        response = await client.get(f"/api/carousels/{uuid4()}/cover-generations")
        assert response.status_code == 404
