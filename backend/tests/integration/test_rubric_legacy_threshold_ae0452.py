"""Listing a rubric stored with a legacy percentage threshold.

Gherkin: tests/features/rubric_evaluation_ae0452.feature
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.integration.test_phase1 import _test_settings, client

__all__ = ["_test_settings", "client"]


async def _store_legacy_rubric() -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models import QualityRubricModel

    async with get_session_maker()() as session:
        session.add(
            QualityRubricModel(
                name="Seeded editorial rubric",
                description="Stored before the fraction scale",
                criteria=[
                    {
                        "id": "clarity",
                        "name": "Clarity",
                        "description": "Clear",
                        "weight": 1.0,
                        "evaluation_method": "ai_auto",
                        "min_threshold": 70.0,
                        "scoring_scale": "0-100",
                        "prompt_template": "Rate {content}",
                    }
                ],
                applicable_content_types=["carousel"],
                is_default=True,
            )
        )
        await session.commit()


@pytest.mark.integration
async def test_listing_reads_legacy_percentage_as_fraction(
    client: AsyncClient,
) -> None:
    # Scenario: A legacy percentage threshold is read as a fraction
    await _store_legacy_rubric()

    response = await client.get("/api/rubrics")

    assert response.status_code == 200, response.text
    criterion = response.json()["items"][0]["criteria"][0]
    assert criterion["min_threshold"] == pytest.approx(0.7)
