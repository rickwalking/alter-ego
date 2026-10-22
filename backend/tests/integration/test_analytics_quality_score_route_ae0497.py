"""GET /api/editorial-analytics returns the content quality score and its count.

Feature: analytics_quality_score_ae0497.feature
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from rag_backend.domain.models import UserRole
from tests.integration.test_phase4_quality import (
    _create_user,
    _test_settings,
    _token,
    client,
)

__all__ = ["_test_settings", "client"]


async def _seed_scores(scores: list[int]) -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.persona_rubric import (
        QualityRubricModel,
        RubricEvaluationScoreModel,
    )

    async with get_session_maker()() as session:
        rubric = QualityRubricModel(name="Checks", criteria=[])
        session.add(rubric)
        await session.flush()
        for overall in scores:
            session.add(
                RubricEvaluationScoreModel(
                    rubric_id=rubric.id,
                    content_id=str(uuid4()),
                    content_type="carousel",
                    scores={},
                    overall_score=overall,
                    passed=overall >= 70,
                    feedback=[],
                )
            )
        await session.commit()


@pytest.mark.asyncio
async def test_route_returns_rounded_average_and_count(client: AsyncClient) -> None:
    # Scenario: The analytics endpoint returns the rounded average and the count
    editor = await _create_user(f"editor-{uuid4().hex[:6]}@test.com", UserRole.EDITOR)
    await _seed_scores([80, 61, 62])

    response = await client.get(
        "/api/editorial-analytics",
        headers={"Authorization": f"Bearer {_token(editor)}"},
    )

    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["quality_score_average"] == 67.7
    assert summary["quality_score_count"] == 3
