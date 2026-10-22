"""The quality rubric on carousel create and the rubric delete guard.

Feature: backend/tests/features/carousel_rubric_ae0504.feature
"""

from __future__ import annotations

from typing import Final

import pytest
from httpx import AsyncClient

_BASE: Final = {"topic": "Julgamento técnico", "audience": "Devs", "niche": "IA"}
_UNKNOWN: Final = "00000000-0000-4000-8000-0000000000ff"


async def _rubric(
    name: str, *, default: bool = False, types: list[str] | None = None
) -> str:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.persona_rubric import (
        QualityRubricModel,
    )

    model = QualityRubricModel(
        name=name,
        criteria=[
            {
                "id": "clarity",
                "name": "Clareza",
                "description": "Uma ideia por slide",
                "weight": 1.0,
                "evaluation_method": "ai_auto",
                "min_threshold": 0.7,
                "scoring_scale": "0-100",
                "prompt_template": "",
            }
        ],
        applicable_content_types=types or ["carousel"],
        is_default=default,
    )
    async with get_session_maker()() as session:
        session.add(model)
        await session.commit()
        return str(model.id)


async def _create(client: AsyncClient, body: dict[str, object]) -> dict[str, object]:
    response = await client.post("/api/carousels", json=body)
    assert response.status_code == 201, response.text
    data: dict[str, object] = response.json()
    return data


@pytest.mark.integration
class TestCreateWithRubric:
    @pytest.mark.asyncio
    async def test_without_rubric_id_the_default_is_stored(
        self, client: AsyncClient
    ) -> None:
        """Scenario: A carousel created without a rubric gets the default carousel rubric."""
        default = await _rubric("Política da casa", default=True)

        data = await _create(client, dict(_BASE))

        assert data["rubric_id"] == default
        read = await client.get(f"/api/carousels/{data['id']}")
        assert read.json()["rubric_id"] == default

    @pytest.mark.asyncio
    async def test_owner_picks_a_rubric_or_none(self, client: AsyncClient) -> None:
        """Scenario: The owner picks a rubric or none in the wizard."""
        await _rubric("Política da casa", default=True)
        qa = await _rubric("QA")

        picked = await _create(client, {**_BASE, "rubric_id": qa})
        none = await _create(client, {**_BASE, "rubric_id": None})

        assert picked["rubric_id"] == qa
        assert none["rubric_id"] is None

    @pytest.mark.asyncio
    async def test_unusable_rubrics_are_refused(self, client: AsyncClient) -> None:
        """Scenario: A rubric that cannot be used is refused at create."""
        blog_only = await _rubric("Blog", types=["blog_post"])

        unknown = await client.post(
            "/api/carousels", json={**_BASE, "rubric_id": _UNKNOWN}
        )
        wrong = await client.post(
            "/api/carousels", json={**_BASE, "rubric_id": blog_only}
        )

        assert unknown.status_code == 404
        assert unknown.json()["detail"] == "rubric_not_found"
        assert wrong.status_code == 422
        assert wrong.json()["detail"] == "rubric_not_for_carousels"


@pytest.mark.integration
class TestRubricDeleteGuard:
    @pytest.mark.asyncio
    async def test_a_rubric_used_by_a_carousel_is_kept(
        self, client: AsyncClient
    ) -> None:
        """Scenario: A rubric used by a carousel cannot be deleted."""
        qa = await _rubric("QA")
        carousel = await _create(client, {**_BASE, "rubric_id": qa})

        refused = await client.delete(f"/api/rubrics/{qa}")

        assert refused.status_code == 409
        assert refused.json()["detail"] == {
            "code": "rubric_in_use",
            "carousels": [{"id": carousel["id"], "topic": _BASE["topic"]}],
        }
        assert (await client.get(f"/api/rubrics/{qa}")).status_code == 200

    @pytest.mark.asyncio
    async def test_an_unused_rubric_is_deleted(self, client: AsyncClient) -> None:
        """Scenario: A rubric used by a carousel cannot be deleted."""
        spare = await _rubric("Spare")

        deleted = await client.delete(f"/api/rubrics/{spare}")

        assert deleted.status_code == 204
        assert (await client.get(f"/api/rubrics/{spare}")).status_code == 404
