"""The owner's slide-1 hook pick (AE-0375).

Gherkin: tests/features/carousel_pov_prompts.feature (Hook pick)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from tests.integration.hook_photo_support import hook_photo_id

_THESIS = "A IA escreve código. Quem decide ainda é você."
_BASE = {"topic": "Julgamento técnico", "audience": "Devs", "niche": "IA"}


async def _create(client: AsyncClient, body: dict[str, object]) -> str:
    response = await client.post("/api/carousels", json=body)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _pov(client: AsyncClient) -> dict[str, object]:
    """A POV create body with an uploaded slide-1 photo (PR #106 review)."""
    photo = await hook_photo_id(client)
    return {
        **_BASE,
        "content_mode": "pov",
        "pov_thesis": _THESIS,
        "hook_asset_id": photo,
    }


async def _set_version(project_id: str, version: str) -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    async with get_session_maker()() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        model.presentation_policy_version = version
        await session.commit()


@pytest.mark.integration
class TestHookPick:
    # Scenario: Owner picks a hook
    @pytest.mark.asyncio
    async def test_pov_hook_is_stored(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        project_id = await _create(client, await _pov(client))
        del asset_dirs
        response = await client.put(
            f"/api/carousels/{project_id}/hook",
            json={"hook_text": "  Pare de pedir   código pra IA  "},
        )
        assert response.status_code == 200, response.text
        assert response.json()["hook_text"] == "Pare de pedir código pra IA"
        fetched = (await client.get(f"/api/carousels/{project_id}")).json()
        assert fetched["hook_text"] == "Pare de pedir código pra IA"

    @pytest.mark.asyncio
    async def test_radar_v4_takes_a_hook(self, client: AsyncClient) -> None:
        project_id = await _create(client, dict(_BASE))
        response = await client.put(
            f"/api/carousels/{project_id}/hook", json={"hook_text": "Todo mundo falou"}
        )
        assert response.status_code == 200

    # Scenario: Hook too long
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "hook",
        [" ".join(["palavra"] * 11), "x" * 61, "   ", ""],
        ids=["11-words", "61-chars", "blank", "empty"],
    )
    async def test_invalid_hook_is_422(
        self, client: AsyncClient, asset_dirs: Path, hook: str
    ) -> None:
        project_id = await _create(client, await _pov(client))
        del asset_dirs
        response = await client.put(
            f"/api/carousels/{project_id}/hook", json={"hook_text": hook}
        )
        assert response.status_code == 422

    # Scenario: Hook on a legacy carousel
    @pytest.mark.asyncio
    async def test_legacy_carousel_is_409(self, client: AsyncClient) -> None:
        project_id = await _create(client, dict(_BASE))
        await _set_version(project_id, "hero_lower_third_v3")
        response = await client.put(
            f"/api/carousels/{project_id}/hook", json={"hook_text": "Gancho"}
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "hook_not_supported_for_this_carousel"

    @pytest.mark.asyncio
    async def test_unknown_carousel_is_404(self, client: AsyncClient) -> None:
        response = await client.put(
            "/api/carousels/00000000-0000-0000-0000-000000000001/hook",
            json={"hook_text": "Gancho"},
        )
        assert response.status_code == 404
