"""The owner's "Gerar capa com Grok" cover on slide 1, and the owner's photo.

Feature: Use the autopilot's generated cover on slide 1
(tests/features/autopilot_cover_autoselect_ae0590.feature). The real app
over an in-memory SQLite database with a fake image bridge editor; the
carousel is paused at a gate unless the test says otherwise.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient

from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from tests.integration.cover_generation_support import (
    BLUE,
    RED,
    FakeEditor,
    generate,
    generation_rows,
    install_fake_editor,
    install_renders,
    project,
    set_project,
)
from tests.integration.hook_photo_support import upload_photo


@pytest.fixture(autouse=True)
def _fresh_limiter() -> Iterator[None]:
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()
    yield
    limiter.reset()


async def _model(project_id: str) -> CarouselProjectModel:
    async with get_session_maker()() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        return model


@pytest.mark.integration
async def test_manual_generation_becomes_slide_one(
    client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A succeeded "Gerar capa com Grok" on a paused carousel is selected."""
    # Scenario: A succeeded manual cover becomes slide 1's cover
    editor: FakeEditor = install_fake_editor(monkeypatch)
    calls = install_renders(monkeypatch)
    photo = await upload_photo(client, RED)
    project_id = await project(client, photo["id"])
    await set_project(project_id, status="drafting", phase_status="awaiting_human")

    await generate(client, project_id, [photo["id"]])

    rows = await generation_rows(project_id)
    assert [row["status"] for row in rows] == ["succeeded"]
    assert len(editor.jobs) == 1
    model = await _model(project_id)
    assert isinstance(model.slide_cover, dict)
    assert model.slide_cover["asset_id"] == rows[0]["result_asset_id"]
    assert model.slide_cover["kind"] == "ai_image"
    assert model.hook_asset_id == photo["id"]
    assert model.lock_version == 5
    assert model.status == "drafting"
    assert calls == []


@pytest.mark.integration
async def test_manual_generation_keeps_a_chosen_cover(
    client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clicking Grok while a cover is already chosen keeps that cover."""
    # Scenario: A manual generation keeps an already chosen cover
    install_fake_editor(monkeypatch)
    photo = await upload_photo(client, RED)
    project_id = await project(client, photo["id"])
    chosen = {
        "asset_id": str(uuid4()),
        "kind": "ai_image",
        "staged_path": "cover.webp",
        "credit": "",
    }
    await set_project(
        project_id,
        status="drafting",
        phase_status="awaiting_human",
        slide_cover=chosen,
    )

    await generate(client, project_id, [photo["id"]])

    rows = await generation_rows(project_id)
    assert [row["status"] for row in rows] == ["succeeded"]
    model = await _model(project_id)
    assert model.slide_cover == chosen
    assert model.lock_version == 4


@pytest.mark.integration
async def test_manual_generation_on_a_completed_carousel_is_an_option(
    client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After completion the cover is only offered: no re-render, no re-approval."""
    # Scenario: A carousel already at the owner's review keeps its cover
    install_fake_editor(monkeypatch)
    calls = install_renders(monkeypatch)
    photo = await upload_photo(client, RED)
    project_id = await project(client, photo["id"])

    await generate(client, project_id, [photo["id"]])

    model = await _model(project_id)
    assert model.slide_cover is None
    assert model.lock_version == 4
    assert model.status == "completed"
    assert calls == []
    options = await client.get(f"/api/carousels/{project_id}/cover-options")
    sources = [option["source"] for option in options.json()["options"]]
    assert "generated" in sources


@pytest.mark.integration
async def test_hook_photo_clears_an_auto_selected_cover(
    client: AsyncClient, asset_dirs: Path
) -> None:
    """The owner's latest slide-1 photo wins over a stored generated cover."""
    # Scenario: Binding a slide-1 photo clears an auto-selected cover
    first = await upload_photo(client, RED)
    second = await upload_photo(client, BLUE)
    project_id = await project(client, first["id"])
    await set_project(
        project_id,
        status="drafting",
        phase_status="awaiting_human",
        slide_cover={
            "asset_id": str(uuid4()),
            "kind": "ai_image",
            "staged_path": "cover.webp",
            "credit": "",
        },
    )

    response = await client.put(
        f"/api/carousels/{project_id}/hook-photo",
        json={"creator_asset_id": second["id"]},
    )

    assert response.status_code == 200, response.text
    async with get_session_maker()() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        assert model.slide_cover is None
        assert model.hook_asset_id == second["id"]
