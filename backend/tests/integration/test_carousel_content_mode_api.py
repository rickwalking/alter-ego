"""Carousel content mode on create and read (AE-0373, ADR-0021).

Gherkin: tests/features/carousel_content_mode.feature
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.integration.hook_photo_support import hook_photo_id

_THESIS = "A IA escreve código. Quem decide ainda é você."
_BASE = {"topic": "Julgamento técnico", "audience": "Devs", "niche": "IA"}
# PR #106 review: a syntactically valid photo id for the schema-level 422 cases;
# the 201 cases upload a real photo (``hook_photo_id``).
_ANY_PHOTO = "00000000-0000-4000-8000-0000000000aa"


def _pov(**changes: object) -> dict[str, object]:
    body: dict[str, object] = {
        **_BASE,
        "content_mode": "pov",
        "pov_thesis": _THESIS,
        "hook_asset_id": _ANY_PHOTO,
    }
    body.update(changes)
    return body


async def _create(client: AsyncClient, body: dict[str, object]) -> dict[str, object]:
    response = await client.post("/api/carousels", json=body)
    assert response.status_code == 201, response.text
    data = response.json()
    assert isinstance(data, dict)
    return data


async def _persona_id() -> str:
    from rag_backend.domain.models.persona import PersonaProfile
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models import PersonaProfileModel

    persona = PersonaProfile(name="Pedro")
    async with get_session_maker()() as session:
        session.add(PersonaProfileModel.from_entity(persona))
        await session.commit()
    return str(persona.id)


@pytest.mark.integration
class TestContentModeDefaults:
    # Scenario: Default mode is Radar IA
    @pytest.mark.asyncio
    async def test_default_mode_is_radar_ia(self, client: AsyncClient) -> None:
        data = await _create(client, dict(_BASE))
        assert data["content_mode"] == "news_analysis"
        assert data["pov_thesis"] is None
        assert data["pov_format"] is None
        assert data["slide_count"] is None
        assert data["cta_goal"] == "follow"

    # Scenario: Existing rows read as Radar IA
    @pytest.mark.asyncio
    async def test_null_mode_reads_as_radar_ia(self, client: AsyncClient) -> None:
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        created = await _create(client, dict(_BASE))
        async with get_session_maker()() as session:
            model = await session.get(CarouselProjectModel, str(created["id"]))
            assert model is not None
            model.content_mode = None
            await session.commit()
        response = await client.get(f"/api/carousels/{created['id']}")
        assert response.status_code == 200
        assert response.json()["content_mode"] == "news_analysis"


@pytest.mark.integration
class TestPovCreate:
    # Scenario: POV project with all fields
    @pytest.mark.asyncio
    async def test_pov_fields_round_trip(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        proof = "No meu último projeto a revisão de arquitetura levou duas horas."
        photo = await hook_photo_id(client)
        data = await _create(
            client,
            _pov(
                hook_asset_id=photo,
                pov_personal_proof=proof,
                pov_format="opiniao",
                slide_count=9,
                cta_goal="send",
            ),
        )
        assert data["content_mode"] == "pov"
        assert data["pov_thesis"] == _THESIS
        assert data["pov_personal_proof"] == proof
        assert data["pov_format"] == "opiniao"
        assert data["slide_count"] == 9
        assert data["cta_goal"] == "send"
        assert data["hook_asset_id"] == photo
        del asset_dirs
        fetched = (await client.get(f"/api/carousels/{data['id']}")).json()
        assert fetched["pov_thesis"] == _THESIS
        assert fetched["slide_count"] == 9

    # Scenario: POV defaults
    @pytest.mark.asyncio
    async def test_pov_defaults(self, client: AsyncClient, asset_dirs: Path) -> None:
        data = await _create(client, _pov(hook_asset_id=await hook_photo_id(client)))
        del asset_dirs
        assert data["pov_format"] == "opiniao"
        assert data["slide_count"] == 9
        assert data["cta_goal"] == "follow"
        assert data["pov_personal_proof"] is None

    # Scenario: Thesis is trimmed
    @pytest.mark.asyncio
    async def test_thesis_is_trimmed(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        photo = await hook_photo_id(client)
        data = await _create(
            client, _pov(pov_thesis=f"  {_THESIS}  ", hook_asset_id=photo)
        )
        del asset_dirs
        assert data["pov_thesis"] == _THESIS


@pytest.mark.integration
class TestContentModeRejections:
    # Scenario: POV without thesis / thesis too long / slide count / format / mode
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "body",
        [
            _pov(pov_thesis="   "),
            {**_BASE, "content_mode": "pov"},
            _pov(pov_thesis="x" * 281),
            _pov(slide_count=7),
            _pov(slide_count=11),
            _pov(pov_format="listicle"),
            {**_BASE, "content_mode": "pov", "pov_thesis": _THESIS},
            {**_BASE, "hook_asset_id": _ANY_PHOTO},
            {**_BASE, "content_mode": "reels"},
            {**_BASE, "cta_goal": "dance"},
            {**_BASE, "pov_thesis": _THESIS},
            {**_BASE, "content_mode": "news_analysis", "pov_format": "opiniao"},
            {**_BASE, "pov_personal_proof": "prova"},
            {**_BASE, "slide_count": 9},
        ],
        ids=[
            "blank-thesis",
            "missing-thesis",
            "thesis-too-long",
            "pov-7-slides",
            "pov-11-slides",
            "unknown-format",
            # PR #106 review: POV needs the slide-1 photo; Radar IA rejects it.
            "pov-missing-photo",
            "photo-on-radar",
            "unknown-mode",
            "unknown-cta-goal",
            "thesis-on-radar",
            "format-on-radar",
            "proof-on-radar",
            "radar-9-slides",
        ],
    )
    async def test_rejected_with_422(
        self, client: AsyncClient, body: dict[str, object]
    ) -> None:
        response = await client.post("/api/carousels", json=body)
        assert response.status_code == 422

    # Scenario: Radar IA with the optional eighth slide
    @pytest.mark.asyncio
    async def test_radar_ia_eight_slides(self, client: AsyncClient) -> None:
        data = await _create(client, {**_BASE, "slide_count": 8})
        assert data["content_mode"] == "news_analysis"
        assert data["slide_count"] == 8


@pytest.mark.integration
class TestPersonaAndTemplate:
    # Scenario: Persona and template are persisted
    @pytest.mark.asyncio
    async def test_persona_and_strategy_persisted(self, client: AsyncClient) -> None:
        persona_id = await _persona_id()
        data = await _create(
            client, {**_BASE, "persona_id": persona_id, "strategy": "feature_grid"}
        )
        assert data["persona_id"] == persona_id
        assert data["slide_layout_strategy"] == "feature_grid"

    # Scenario: Unknown persona
    @pytest.mark.asyncio
    async def test_unknown_persona_is_404(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/carousels", json={**_BASE, "persona_id": str(uuid4())}
        )
        assert response.status_code == 404
        listed = (await client.get("/api/carousels")).json()
        assert listed["total"] == 0
