"""The picker guard and the website cover switch, over HTTP.

Feature: tests/features/website_cover_review_switch_ae0594.feature and
tests/features/reopen_review_on_cover_switch_ae0597.feature. The real app over
SQLite (no checkpointer, so only the row's review is reopened); the republish
render and the GrokBot offer are stubbed.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_SWITCH_REQUIRES_REVIEW,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.editorial.infrastructure import (
    carousel_owner_autofix,
    cover_review_rollback,
)
from tests.integration.cover_generation_support import (
    BLUE,
    RED,
    generate,
    generation_rows,
    install_fake_editor,
    install_renders,
    project,
    set_project,
    slide_cover,
)
from tests.integration.hook_photo_support import upload_photo


@pytest.fixture(autouse=True)
def _fresh_limiter() -> Iterator[None]:
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()
    yield
    limiter.reset()


async def _pick(
    client: AsyncClient, values: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> tuple[int, object, list[str]]:
    calls = install_renders(monkeypatch)
    first = await upload_photo(client, RED)
    second = await upload_photo(client, BLUE)
    project_id = await project(client, first["id"])
    await set_project(project_id, **values)
    response = await client.put(
        f"/api/carousels/{project_id}/cover",
        json={"asset_id": second["id"], "expected_version": 4},
    )
    return response.status_code, response.json().get("detail"), calls


@pytest.mark.integration
@pytest.mark.parametrize(
    "values",
    [
        {"workflow_status": "approved_for_publish", "is_public": True},
        {"is_public": True},
    ],
)
async def test_pick_on_a_published_carousel_is_refused(
    client: AsyncClient,
    asset_dirs: Path,
    monkeypatch: pytest.MonkeyPatch,
    values: dict[str, object],
) -> None:
    """409 ``cover_switch_requires_review`` and nothing is rendered."""
    # Scenario: The picker refuses a published carousel
    # Scenario: A published carousel never changes
    status, detail, calls = await _pick(client, values, monkeypatch)

    assert status == 409
    assert detail == ERR_COVER_SWITCH_REQUIRES_REVIEW
    assert calls == []


@pytest.mark.integration
async def test_pick_on_a_carousel_in_review_still_switches(
    client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A draft carousel in final review is switched as before."""
    # Scenario: A carousel waiting for its first approval switches and stays in review
    status, _detail, calls = await _pick(
        client, {"workflow_status": "draft"}, monkeypatch
    )

    assert status == 200
    assert len(calls) == 1


@pytest.mark.integration
async def test_route_switches_a_completed_carousel_in_final_review(
    client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``POST /cover-generations`` composes the review switch: slide 1 moves."""
    # Scenario: A website cover switches a completed carousel in final review
    install_fake_editor(monkeypatch)
    install_renders(monkeypatch)
    calls: list[str] = []

    async def _finalize(_session: AsyncSession, project_id: str) -> tuple[str, ...]:
        calls.append(project_id)
        return ()

    monkeypatch.setattr(cover_review_rollback, "_finalize", _finalize)
    photo = await upload_photo(client, RED)
    project_id = await project(client, photo["id"])
    await set_project(project_id, current_phase="final_review", workflow_status="draft")

    await generate(client, project_id, [photo["id"]])

    rows = await generation_rows(project_id)
    cover = await slide_cover(project_id)
    assert cover["asset_id"] == rows[0]["result_asset_id"]
    assert cover["kind"] == "ai_image"
    assert calls == [project_id]


async def _bind(
    client: AsyncClient, values: dict[str, object]
) -> tuple[str, object, int]:
    first = await upload_photo(client, RED)
    second = await upload_photo(client, BLUE)
    project_id = await project(client, first["id"])
    await set_project(project_id, **values)
    response = await client.put(
        f"/api/carousels/{project_id}/hook-photo",
        json={"creator_asset_id": second["id"]},
    )
    return project_id, response.json().get("detail"), response.status_code


@pytest.mark.integration
async def test_hook_photo_on_a_published_carousel_is_refused(
    client: AsyncClient, asset_dirs: Path
) -> None:
    """``PUT /hook-photo`` follows the picker's rule: 409 and nothing written."""
    # Scenario: The picker refuses a published carousel
    project_id, detail, status = await _bind(client, {"is_public": True})

    assert status == 409
    assert detail == ERR_COVER_SWITCH_REQUIRES_REVIEW
    assert (await _model(project_id)).needs_republish_since is None


@pytest.mark.integration
async def test_hook_photo_on_a_completed_carousel_waits_for_a_render(
    client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A completed carousel in review goes through the cover switch: the marker
    is set while it renders, so approval waits for the render, then cleared."""
    # Scenario: No approval lands while a cover switch is between write and render
    marked: list[bool] = []

    async def _render(_self: object, project_id: str) -> tuple[str, ...]:
        marked.append((await _model(project_id)).needs_republish_since is not None)
        return ()

    monkeypatch.setattr(carousel_owner_autofix.RepublishRenderer, "render", _render)
    project_id, _detail, status = await _bind(client, {"workflow_status": "draft"})

    assert status == 200
    assert marked == [True]
    model = await _model(project_id)
    assert model.needs_republish_since is None
    assert model.lock_version == 5


async def _model(project_id: str) -> CarouselProjectModel:
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        return model
