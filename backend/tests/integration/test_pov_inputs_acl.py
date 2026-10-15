"""Persona and slide-1 photo lookups for the autopilot (PR #106 review, items 3-4).

Gherkin: tests/features/autopilot_pov_thesis.feature
("Persona and voice gate", "Slide-1 photo" sections)
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient

from rag_backend.domain.constants.creator_asset import build_creator_asset_filename
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.modules.autopilot.infrastructure.project_inputs import (
    SqlProjectInputs,
)
from rag_backend.modules.editorial.public import (
    AutomationStart,
    CarouselAutomationAcl,
    PovInputsAcl,
)
from tests.integration.hook_photo_support import png, upload_photo

_THESIS = "A IA escreve código. Quem decide ainda é você."


async def _persona(name: str) -> str:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models import PersonaProfileModel

    persona = PersonaProfile(name=name)
    async with get_session_maker()() as session:
        session.add(PersonaProfileModel.from_entity(persona))
        await session.commit()
    return str(persona.id)


async def _hook_photo(owner_id: str) -> str | None:
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        return await PovInputsAcl(session).hook_photo_id(owner_id)


async def _resolve(configured: str) -> str | None:
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        return await SqlProjectInputs(session, configured).persona_id()


async def _pov_project(client: AsyncClient, photo_id: object) -> str:
    response = await client.post(
        "/api/carousels",
        json={
            "topic": "T",
            "audience": "Devs",
            "niche": "IA",
            "content_mode": "pov",
            "pov_thesis": _THESIS,
            "hook_asset_id": photo_id,
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


@pytest.mark.integration
class TestHookPhotoChoice:
    # Scenario: The most recently used hook photo is preferred
    @pytest.mark.asyncio
    async def test_prefers_the_recently_used_photo(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        older = await upload_photo(client, (1, 1, 1, 0))
        await upload_photo(client, (2, 2, 2, 0))
        await _pov_project(client, older["id"])
        assert await _hook_photo(str(older["owner_id"])) == older["id"]
        del asset_dirs

    # Scenario: Without a used photo the newest hook photo is picked
    @pytest.mark.asyncio
    async def test_falls_back_to_the_newest_hook_photo(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        await upload_photo(client, (1, 1, 1, 0))
        newest = await upload_photo(client, (2, 2, 2, 0))
        cta = await client.post(
            "/api/carousels/creator-assets",
            files={"file": ("cta.png", png((3, 3, 3, 0)), "image/png")},
            data={"role": "cta"},
        )
        assert cta.status_code == 201
        assert await _hook_photo(str(newest["owner_id"])) == newest["id"]
        del asset_dirs

    # Scenario: An unreadable hook photo counts as missing
    @pytest.mark.asyncio
    async def test_skips_a_photo_whose_file_is_gone(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        older = await upload_photo(client, (1, 1, 1, 0))
        newest = await upload_photo(client, (2, 2, 2, 0))
        stored = (
            asset_dirs
            / "assets"
            / build_creator_asset_filename(str(newest["content_sha256"]))
        )
        stored.unlink()
        assert await _hook_photo(str(older["owner_id"])) == older["id"]
        (
            asset_dirs
            / "assets"
            / build_creator_asset_filename(str(older["content_sha256"]))
        ).unlink()
        assert await _hook_photo(str(older["owner_id"])) is None

    # Scenario: No hook photo
    @pytest.mark.asyncio
    async def test_no_photo_or_no_owner_is_none(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        assert await _hook_photo("someone") is None
        assert await _hook_photo("") is None
        del client, asset_dirs


@pytest.mark.integration
class TestPersonaResolution:
    # Scenario: AUTOPILOT_PERSONA_ID names an existing persona
    @pytest.mark.asyncio
    async def test_configured_persona_wins(self, client: AsyncClient) -> None:
        configured = await _persona("Outra voz")
        await _persona("Pedro")
        assert await _resolve(configured) == configured
        del client

    # Scenario: Empty (or unknown) AUTOPILOT_PERSONA_ID falls back to "Pedro"
    @pytest.mark.asyncio
    @pytest.mark.parametrize("configured", ["", "  ", "not-a-persona"])
    async def test_falls_back_to_pedro_by_name(
        self, client: AsyncClient, configured: str
    ) -> None:
        pedro = await _persona("pedro")
        assert await _resolve(configured) == pedro
        del client

    # Scenario: No persona at all
    @pytest.mark.asyncio
    async def test_none_without_a_pedro(self, client: AsyncClient) -> None:
        await _persona("Outra voz")
        assert await _resolve("") is None
        del client


@pytest.mark.integration
class TestAutomationAcl:
    # Scenario: The autopilot carousel stages its slide-1 photo
    @pytest.mark.asyncio
    async def test_create_stages_the_photo_and_start_loads_the_persona(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        from rag_backend.infrastructure.database.config import get_session_maker

        photo = await upload_photo(client, (4, 4, 4, 0))
        persona = await _persona("Pedro")
        async with get_session_maker()() as session:
            acl = CarouselAutomationAcl(session)
            project_id = await acl.create_project(
                CarouselProject(
                    topic="T",
                    audience="Devs",
                    niche="IA",
                    content_mode="pov",
                    pov_thesis=_THESIS,
                    hook_asset_id=UUID(str(photo["id"])),
                    persona_id=persona,
                    owner_id=str(photo["owner_id"]),
                )
            )
            await session.commit()
            assert await acl.is_pov(project_id)
            start = await acl.start_input(
                AutomationStart(
                    topic="T",
                    audience="Devs",
                    brief="b",
                    sources=(),
                    user_id="u",
                    persona_id=persona,
                )
            )
            unvoiced = await acl.start_input(
                AutomationStart(
                    topic="T", audience="Devs", brief="b", sources=(), user_id="u"
                )
            )
        staged = asset_dirs / "output" / project_id / str(photo["relative_path"])
        assert staged.is_file()
        assert start.persona is not None
        assert str(start.persona.id) == persona
        assert unvoiced.persona is None
