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


async def _seed_scores(scores: list[int], content_ids: list[str] | None = None) -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.persona_rubric import (
        QualityRubricModel,
        RubricEvaluationScoreModel,
    )

    async with get_session_maker()() as session:
        rubric = QualityRubricModel(name="Checks", criteria=[])
        session.add(rubric)
        await session.flush()
        ids = content_ids or [str(uuid4()) for _ in scores]
        for overall, content_id in zip(scores, ids, strict=True):
            session.add(
                RubricEvaluationScoreModel(
                    rubric_id=rubric.id,
                    content_id=content_id,
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
    """Scenario: The analytics endpoint returns the rounded average and the count.

    An admin's average counts every content score.
    """
    admin = await _create_user(f"admin-{uuid4().hex[:6]}@test.com", UserRole.ADMIN)
    await _seed_scores([80, 61, 62])

    response = await client.get(
        "/api/editorial-analytics",
        headers={"Authorization": f"Bearer {_token(admin)}"},
    )

    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["quality_score_average"] == 67.7
    assert summary["quality_score_count"] == 3


async def _carousel_of(owner_id: str) -> str:
    from rag_backend.domain.models import CarouselProject, CarouselTheme
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        created = await PostgresCarouselRepository(session).create_project(
            CarouselProject(
                topic="Scored",
                audience="Devs",
                niche="IA",
                theme=CarouselTheme.AI_COMPETITION,
                owner_id=owner_id,
            )
        )
        await session.commit()
        return str(created.id)


@pytest.mark.asyncio
async def test_an_editor_averages_only_their_own_content(client: AsyncClient) -> None:
    """Scenario: The quality average counts only the caller's own content."""
    editor = await _create_user(f"editor-{uuid4().hex[:6]}@test.com", UserRole.EDITOR)
    other = await _create_user(f"other-{uuid4().hex[:6]}@test.com", UserRole.EDITOR)
    mine = await _carousel_of(str(editor.id))
    theirs = await _carousel_of(str(other.id))
    await _seed_scores([90, 40], [mine, theirs])

    response = await client.get(
        "/api/editorial-analytics",
        headers={"Authorization": f"Bearer {_token(editor)}"},
    )

    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["quality_score_average"] == 90.0
    assert summary["quality_score_count"] == 1
