"""The picker guard and the website cover switch, over HTTP.

Feature: tests/features/website_cover_review_switch_ae0594.feature. The real
app over SQLite; the republish render and the GrokBot offer are stubbed.
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
from rag_backend.modules.editorial.infrastructure import cover_review_rollback
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
        {"workflow_status": "approved_for_publish"},
        {"workflow_status": "approved_for_publish", "is_public": True},
        {"is_public": True},
    ],
)
async def test_pick_on_an_approved_or_published_carousel_is_refused(
    client: AsyncClient,
    asset_dirs: Path,
    monkeypatch: pytest.MonkeyPatch,
    values: dict[str, object],
) -> None:
    """409 ``cover_switch_requires_review`` and nothing is rendered."""
    # Scenario: The picker refuses an approved carousel
    # Scenario: The picker refuses a published carousel
    status, detail, calls = await _pick(client, values, monkeypatch)

    assert status == 409
    assert detail == ERR_COVER_SWITCH_REQUIRES_REVIEW
    assert calls == []


@pytest.mark.integration
async def test_pick_on_a_carousel_in_review_still_switches(
    client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A draft carousel in final review is switched as before."""
    # Scenario: The picker refuses an approved carousel
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
