"""Rubric create and update reject thresholds above 1.0.

Gherkin: tests/features/rubric_evaluation_ae0452.feature
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.integration.test_phase1 import _test_settings, client

__all__ = ["_test_settings", "client"]


def _payload(threshold: float) -> dict[str, object]:
    return {
        "name": "Threshold rubric",
        "description": "Thresholds are fractions",
        "criteria": [
            {
                "id": "clarity",
                "name": "Clarity",
                "description": "Clear",
                "weight": 1.0,
                "evaluation_method": "ai_auto",
                "min_threshold": threshold,
                "scoring_scale": "0-100",
                "prompt_template": "Rate {content}",
            }
        ],
        "applicable_content_types": ["carousel"],
        "is_default": False,
    }


@pytest.mark.integration
@pytest.mark.parametrize("threshold", [1.5, 7, 70])
async def test_create_rejects_a_threshold_above_one(
    client: AsyncClient, threshold: float
) -> None:
    # Scenario: Creating or updating a rubric with a threshold above 1.0 is rejected
    response = await client.post("/api/rubrics", json=_payload(threshold))
    listing = await client.get("/api/rubrics")

    assert response.status_code == 422, response.text
    assert listing.json()["total"] == 0


@pytest.mark.integration
@pytest.mark.parametrize("threshold", [1.5, 7, 70])
async def test_update_rejects_a_threshold_above_one(
    client: AsyncClient, threshold: float
) -> None:
    # Scenario: Creating or updating a rubric with a threshold above 1.0 is rejected
    created = await client.post("/api/rubrics", json=_payload(0.7))
    rubric_id = created.json()["id"]

    response = await client.put(
        f"/api/rubrics/{rubric_id}", json={"criteria": _payload(threshold)["criteria"]}
    )
    stored = await client.get(f"/api/rubrics/{rubric_id}")

    assert created.status_code == 201, created.text
    assert response.status_code == 422, response.text
    assert stored.json()["criteria"][0]["min_threshold"] == pytest.approx(0.7)


async def _seed_legacy_rubric() -> str:
    from sqlalchemy.ext.asyncio import AsyncSession

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.infrastructure.database.models import QualityRubricModel

    assert db_config.c_engine is not None
    legacy = _payload(0.7)
    criteria = legacy["criteria"]
    assert isinstance(criteria, list)
    async with AsyncSession(db_config.c_engine, expire_on_commit=False) as session:
        rubric = QualityRubricModel(
            name="Seeded legacy rubric",
            description="Stored before the fraction scale",
            criteria=[{**criteria[0], "min_threshold": 70.0}],
            applicable_content_types=["carousel"],
            is_default=False,
        )
        session.add(rubric)
        await session.commit()
        return str(rubric.id)


@pytest.mark.integration
async def test_an_edited_legacy_rubric_saves(client: AsyncClient) -> None:
    # Scenario: An edited legacy rubric saves
    rubric_id = await _seed_legacy_rubric()
    read = await client.get(f"/api/rubrics/{rubric_id}")

    saved = await client.put(
        f"/api/rubrics/{rubric_id}", json={"criteria": read.json()["criteria"]}
    )
    stored = await client.get(f"/api/rubrics/{rubric_id}")

    assert read.status_code == 200, read.text
    assert read.json()["criteria"][0]["min_threshold"] == pytest.approx(0.7)
    assert saved.status_code == 200, saved.text
    assert stored.json()["criteria"][0]["min_threshold"] == pytest.approx(0.7)
