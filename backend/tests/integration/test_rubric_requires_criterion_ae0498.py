"""Rubric create and update reject an empty criteria list.

Gherkin: tests/features/rubric_requires_criterion_ae0498.feature
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.integration.test_phase1 import _test_settings, client

__all__ = ["_test_settings", "client"]

CRITERION: dict[str, object] = {
    "id": "clarity",
    "name": "Clarity",
    "description": "Clear",
    "weight": 1.0,
    "evaluation_method": "ai_auto",
    "min_threshold": 0.7,
    "scoring_scale": "0-100",
    "prompt_template": "Rate {content}",
}


def _payload(criteria: list[dict[str, object]] | None) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Criteria rubric",
        "description": "Needs criteria",
        "applicable_content_types": ["carousel"],
        "is_default": False,
    }
    if criteria is not None:
        payload["criteria"] = criteria
    return payload


@pytest.mark.integration
@pytest.mark.parametrize("criteria", [[], None])
async def test_create_without_criteria_is_rejected(
    client: AsyncClient, criteria: list[dict[str, object]] | None
) -> None:
    # Scenario: Creating a rubric without criteria is rejected
    response = await client.post("/api/rubrics", json=_payload(criteria))
    listing = await client.get("/api/rubrics")

    assert response.status_code == 422, response.text
    assert listing.json()["total"] == 0


@pytest.mark.integration
async def test_update_to_no_criteria_is_rejected(client: AsyncClient) -> None:
    # Scenario: Updating a rubric to no criteria is rejected
    created = await client.post("/api/rubrics", json=_payload([CRITERION]))
    rubric_id = created.json()["id"]

    response = await client.put(f"/api/rubrics/{rubric_id}", json={"criteria": []})
    stored = await client.get(f"/api/rubrics/{rubric_id}")

    assert response.status_code == 422, response.text
    assert [c["id"] for c in stored.json()["criteria"]] == ["clarity"]


@pytest.mark.integration
async def test_update_without_criteria_keeps_them(client: AsyncClient) -> None:
    # Scenario: An update without criteria keeps the stored criteria
    created = await client.post("/api/rubrics", json=_payload([CRITERION]))
    rubric_id = created.json()["id"]

    response = await client.put(f"/api/rubrics/{rubric_id}", json={"name": "Renamed"})

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Renamed"
    assert [c["id"] for c in response.json()["criteria"]] == ["clarity"]
