"""The owner's photo library and the POV slide-1 photo (AE-0376).

Gherkin: tests/features/carousel_pov_layouts.feature (Photo library)
"""

from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO
from pathlib import Path

import pytest
from httpx import AsyncClient

from rag_backend.domain.models import UserRole
from tests.integration.conftest import auth_headers_for, create_test_user

_THESIS = "A IA escreve código. Quem decide ainda é você."


def _png(color: tuple[int, int, int, int]) -> bytes:
    from PIL import Image

    buffer = BytesIO()
    Image.new("RGBA", (16, 20), color).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def asset_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    from rag_backend.infrastructure.config.settings import get_settings

    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "output"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


async def _upload(
    client: AsyncClient,
    color: tuple[int, int, int, int],
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
    response = await client.post(
        "/api/carousels/creator-assets",
        files={"file": ("me.png", _png(color), "image/png")},
        data={"role": "hook", "pose_tag": "Apontando"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert isinstance(body, dict)
    return body


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

        own_image = await client.get(f"/api/carousels/creator-assets/{mine['id']}/image")
        assert own_image.status_code == 200
        assert own_image.headers["content-type"] == "image/webp"
        foreign = await client.get(f"/api/carousels/creator-assets/{theirs['id']}/image")
        assert foreign.status_code == 403
        del asset_dirs

    @pytest.mark.asyncio
    async def test_invalid_role_is_422(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        response = await client.post(
            "/api/carousels/creator-assets",
            files={"file": ("me.png", _png((1, 2, 3, 4)), "image/png")},
            data={"role": "villain"},
        )
        assert response.status_code == 422
        listed = await client.get("/api/carousels/creator-assets?role=villain")
        assert listed.status_code == 422
        del asset_dirs

    @pytest.mark.asyncio
    async def test_unknown_image_is_400(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        response = await client.get(
            "/api/carousels/creator-assets/00000000-0000-0000-0000-000000000001/image"
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "creator_asset_not_found"
        del asset_dirs


@pytest.mark.integration
class TestHookPhoto:
    # Scenario: Slide-1 photo for a POV carousel
    @pytest.mark.asyncio
    async def test_bind_and_stage(self, client: AsyncClient, asset_dirs: Path) -> None:
        photo = await _upload(client, (9, 9, 9, 0))
        created = await client.post(
            "/api/carousels",
            json={
                "topic": "T",
                "audience": "Devs",
                "niche": "IA",
                "content_mode": "pov",
                "pov_thesis": _THESIS,
            },
        )
        project_id = created.json()["id"]
        response = await client.put(
            f"/api/carousels/{project_id}/hook-photo",
            json={"creator_asset_id": photo["id"]},
        )
        assert response.status_code == 200, response.text
        assert response.json()["hook_asset_id"] == photo["id"]
        fetched = (await client.get(f"/api/carousels/{project_id}")).json()
        assert fetched["hook_asset_id"] == photo["id"]
        staged = asset_dirs / "output" / project_id / str(photo["relative_path"])
        assert staged.is_file()

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
