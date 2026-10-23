"""The owner's photo library and the POV slide-1 photo.

Gherkin: tests/features/carousel_pov_layouts.feature (Photo library)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from rag_backend.domain.models import UserRole
from tests.integration.conftest import auth_headers_for, create_test_user
from tests.integration.hook_photo_support import png, upload_photo

_THESIS = "A IA escreve código. Quem decide ainda é você."


def _pov(photo_id: object) -> dict[str, object]:
    return {
        "topic": "T",
        "audience": "Devs",
        "niche": "IA",
        "content_mode": "pov",
        "pov_thesis": _THESIS,
        "hook_asset_id": photo_id,
    }


async def _upload(
    client: AsyncClient,
    color: tuple[int, int, int, int],
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
    return await upload_photo(client, color, headers)


@pytest.mark.integration
class TestPhotoLibrary:
    # Scenario: Photo library is owner scoped
    @pytest.mark.asyncio
    async def test_owner_scoped(self, client: AsyncClient, asset_dirs: Path) -> None:
        mine = await _upload(client, (255, 0, 0, 0))
        assert mine["role"] == "hook"
        assert mine["pose_tag"] == "Apontando"
        other = await create_test_user("other@integration.test", UserRole.EDITOR)
        theirs = await _upload(
            client, (0, 255, 0, 255), headers=auth_headers_for(other)
        )

        listed = (await client.get("/api/carousels/creator-assets?role=hook")).json()
        ids = [item["id"] for item in listed["items"]]
        assert ids == [mine["id"]]
        empty = (await client.get("/api/carousels/creator-assets?role=cta")).json()
        assert empty["items"] == []

        own_image = await client.get(
            f"/api/carousels/creator-assets/{mine['id']}/image"
        )
        assert own_image.status_code == 200
        assert own_image.headers["content-type"] == "image/webp"
        foreign = await client.get(
            f"/api/carousels/creator-assets/{theirs['id']}/image"
        )
        assert foreign.status_code == 403
        del asset_dirs

    @pytest.mark.asyncio
    async def test_invalid_role_is_422(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        response = await client.post(
            "/api/carousels/creator-assets",
            files={"file": ("me.png", png((1, 2, 3, 4)), "image/png")},
            data={"role": "villain"},
        )
        assert response.status_code == 422
        listed = await client.get("/api/carousels/creator-assets?role=villain")
        assert listed.status_code == 422
        del asset_dirs

    @pytest.mark.asyncio
    async def test_unknown_image_is_404(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        response = await client.get(
            "/api/carousels/creator-assets/00000000-0000-0000-0000-000000000001/image"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "creator_asset_not_found"
        del asset_dirs


@pytest.mark.integration
class TestHookPhoto:
    # Scenario: Slide-1 photo for a POV carousel (chosen at create, PR #106)
    @pytest.mark.asyncio
    async def test_create_binds_and_stages(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        photo = await _upload(client, (9, 9, 9, 0))
        created = await client.post("/api/carousels", json=_pov(photo["id"]))
        assert created.status_code == 201, created.text
        project_id = created.json()["id"]
        assert created.json()["hook_asset_id"] == photo["id"]
        fetched = (await client.get(f"/api/carousels/{project_id}")).json()
        assert fetched["hook_asset_id"] == photo["id"]
        staged = asset_dirs / "output" / project_id / str(photo["relative_path"])
        assert staged.is_file()

    # Scenario: The owner swaps the slide-1 photo later
    @pytest.mark.asyncio
    async def test_put_rebinds_and_stages(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        first = await _upload(client, (9, 9, 9, 0))
        second = await _upload(client, (8, 8, 8, 0))
        created = await client.post("/api/carousels", json=_pov(first["id"]))
        project_id = created.json()["id"]
        response = await client.put(
            f"/api/carousels/{project_id}/hook-photo",
            json={"creator_asset_id": second["id"]},
        )
        assert response.status_code == 200, response.text
        assert response.json()["hook_asset_id"] == second["id"]
        staged = asset_dirs / "output" / project_id / str(second["relative_path"])
        assert staged.is_file()

    # Scenario: POV create without the slide-1 photo is a 422
    @pytest.mark.asyncio
    async def test_pov_create_without_photo_is_422(self, client: AsyncClient) -> None:
        body = _pov("")
        del body["hook_asset_id"]
        response = await client.post("/api/carousels", json=body)
        assert response.status_code == 422
        assert "hook_asset_id is required" in response.text

    # Scenario: POV create with an unknown photo creates nothing
    @pytest.mark.asyncio
    async def test_pov_create_with_unknown_photo_is_400(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        unknown = "00000000-0000-4000-8000-000000000001"
        response = await client.post("/api/carousels", json=_pov(unknown))
        assert response.status_code == 400
        assert response.json()["detail"] == "creator_asset_not_found"
        listed = (await client.get("/api/carousels")).json()
        assert all(item["topic"] != "T" for item in listed["items"])
        del asset_dirs

    # Scenario: POV create with another user's photo is a 403
    @pytest.mark.asyncio
    async def test_pov_create_with_foreign_photo_is_403(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        other = await create_test_user("owner3@integration.test", UserRole.EDITOR)
        theirs = await _upload(client, (6, 6, 6, 6), headers=auth_headers_for(other))
        response = await client.post("/api/carousels", json=_pov(theirs["id"]))
        assert response.status_code == 403
        del asset_dirs

    # Scenario: Radar IA create rejects a slide-1 photo
    @pytest.mark.asyncio
    async def test_radar_create_with_photo_is_422(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        photo = await _upload(client, (7, 7, 7, 0))
        body = {"topic": "T", "audience": "Devs", "niche": "IA"}
        response = await client.post(
            "/api/carousels", json={**body, "hook_asset_id": photo["id"]}
        )
        assert response.status_code == 422
        del asset_dirs

    @pytest.mark.asyncio
    async def test_foreign_photo_is_403(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        other = await create_test_user("owner2@integration.test", UserRole.EDITOR)
        theirs = await _upload(client, (5, 5, 5, 5), headers=auth_headers_for(other))
        created = await client.post(
            "/api/carousels", json={"topic": "T", "audience": "Devs", "niche": "IA"}
        )
        response = await client.put(
            f"/api/carousels/{created.json()['id']}/hook-photo",
            json={"creator_asset_id": theirs["id"]},
        )
        assert response.status_code == 403
        del asset_dirs
