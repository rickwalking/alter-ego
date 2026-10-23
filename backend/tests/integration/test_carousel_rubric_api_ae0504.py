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

        not_a_uuid = await client.post(
            "/api/carousels", json={**_BASE, "rubric_id": "not-a-uuid"}
        )

        assert not_a_uuid.status_code == 422
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
            "other_carousels": 0,
        }
        assert (await client.get(f"/api/rubrics/{qa}")).status_code == 200

    @pytest.mark.asyncio
    async def test_an_unused_rubric_is_deleted(self, client: AsyncClient) -> None:
        """Scenario: A rubric used by a carousel cannot be deleted."""
        spare = await _rubric("Spare")

        deleted = await client.delete(f"/api/rubrics/{spare}")

        assert deleted.status_code == 204
        assert (await client.get(f"/api/rubrics/{spare}")).status_code == 404

    @pytest.mark.asyncio
    async def test_a_default_rubric_in_use_names_its_carousels(
        self, client: AsyncClient
    ) -> None:
        """Scenario: A rubric used by a carousel cannot be deleted."""
        default = await _rubric("Política da casa", default=True)
        carousel = await _create(client, dict(_BASE))

        refused = await client.delete(f"/api/rubrics/{default}")

        assert refused.status_code == 409
        assert refused.json()["detail"]["carousels"] == [
            {"id": carousel["id"], "topic": _BASE["topic"]}
        ]


async def _carousel_of_someone_else(rubric_id: str) -> str:
    from rag_backend.domain.models import CarouselProject, CarouselTheme
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        created = await PostgresCarouselRepository(session).create_project(
            CarouselProject(
                topic="Segredo de outra pessoa",
                audience="Devs",
                niche="IA",
                theme=CarouselTheme.AI_COMPETITION,
                owner_id="someone-else",
                rubric_id=rubric_id,
            )
        )
        await session.commit()
        return str(created.id)


@pytest.mark.integration
class TestRubricDeleteScoping:
    @pytest.mark.asyncio
    async def test_an_editor_sees_only_own_carousels_and_a_count(
        self, client: AsyncClient
    ) -> None:
        """Scenario: A rubric used by a carousel cannot be deleted."""
        qa = await _rubric("QA")
        mine = await _create(client, {**_BASE, "rubric_id": qa})
        await _carousel_of_someone_else(qa)

        refused = await client.delete(f"/api/rubrics/{qa}")

        detail = refused.json()["detail"]
        assert refused.status_code == 409
        assert detail["carousels"] == [{"id": mine["id"], "topic": _BASE["topic"]}]
        assert detail["other_carousels"] == 1
        assert "Segredo de outra pessoa" not in refused.text

    @pytest.mark.asyncio
    async def test_an_admin_sees_every_carousel(self, client: AsyncClient) -> None:
        """Scenario: A rubric used by a carousel cannot be deleted."""
        from rag_backend.domain.models import UserRole
        from tests.integration.conftest import auth_headers_for, create_test_user

        qa = await _rubric("QA")
        await _create(client, {**_BASE, "rubric_id": qa})
        await _carousel_of_someone_else(qa)
        admin = await create_test_user("admin@integration.test", UserRole.ADMIN)

        refused = await client.delete(
            f"/api/rubrics/{qa}", headers=auth_headers_for(admin)
        )

        detail = refused.json()["detail"]
        assert len(detail["carousels"]) == 2
        assert detail["other_carousels"] == 0


def _criterion(**changes: object) -> dict[str, object]:
    criterion: dict[str, object] = {
        "id": "clarity",
        "name": "Clareza",
        "description": "Uma ideia por slide",
        "weight": 1.0,
        "evaluation_method": "ai_auto",
        "min_threshold": 0.7,
        "scoring_scale": "0-100",
        "prompt_template": "",
    }
    criterion.update(changes)
    return criterion


@pytest.mark.integration
class TestRubricInputBounds:
    @pytest.mark.asyncio
    async def test_criterion_text_and_count_are_bounded(
        self, client: AsyncClient
    ) -> None:
        """Scenario: A rubric's criteria are bounded before they reach a prompt."""
        long_text = "x" * 1001
        too_long = await client.post(
            "/api/rubrics",
            json={"name": "Longa", "criteria": [_criterion(description=long_text)]},
        )
        too_long_prompt = await client.post(
            "/api/rubrics",
            json={"name": "Longa", "criteria": [_criterion(prompt_template=long_text)]},
        )
        too_many = await client.post(
            "/api/rubrics",
            json={
                "name": "Muitas",
                "criteria": [_criterion(id=f"c{i}") for i in range(13)],
            },
        )
        at_the_limit = await client.post(
            "/api/rubrics",
            json={
                "name": "No limite",
                "criteria": [
                    _criterion(id=f"c{i}", description="x" * 1000) for i in range(12)
                ],
            },
        )

        assert too_long.status_code == 422
        assert too_long_prompt.status_code == 422
        assert too_many.status_code == 422
        assert at_the_limit.status_code == 201, at_the_limit.text

    @pytest.mark.asyncio
    async def test_an_edit_bumps_the_version_and_old_long_text_still_reads(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Stored scores keep the rubric version they were given under."""
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models.persona_rubric import (
            QualityRubricModel,
        )

        rubric_id = await _rubric("Antiga")
        async with get_session_maker()() as session:
            model = await session.get(QualityRubricModel, rubric_id)
            assert model is not None
            model.criteria = [_criterion(description="y" * 1500)]
            await session.commit()

        read = await client.get(f"/api/rubrics/{rubric_id}")
        edited = await client.put(f"/api/rubrics/{rubric_id}", json={"name": "Nova"})

        assert read.status_code == 200
        assert len(read.json()["criteria"][0]["description"]) == 1500
        assert edited.status_code == 200
        async with get_session_maker()() as session:
            model = await session.get(QualityRubricModel, rubric_id)
            assert model is not None
            assert model.version == 2
