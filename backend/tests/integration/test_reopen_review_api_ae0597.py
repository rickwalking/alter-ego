"""The picker and the hook photo reopen an approved carousel's review, over HTTP.

Feature: tests/features/reopen_review_on_cover_switch_ae0597.feature. The real
app over SQLite; the republish render is stubbed, the checkpoint reopen is
stubbed (there is no LangGraph thread here) and the autopilot ``reopened``
hook is recorded.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient

from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_SWITCH_REQUIRES_REVIEW,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.infrastructure.cover_review_hold import (
    SessionCoverReviewHold,
)
from rag_backend.modules.editorial.infrastructure import (
    carousel_owner_autofix,
    review_reopen,
)
from tests.integration.cover_generation_support import (
    BLUE,
    RED,
    install_renders,
    project,
    set_project,
)
from tests.integration.hook_photo_support import upload_photo

_APPROVED: dict[str, object] = {
    "workflow_status": "approved_for_publish",
    "current_phase": "final_review",
    "phase_status": "approved",
}


@pytest.fixture(autouse=True)
def _fresh_limiter() -> Iterator[None]:
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()
    yield
    limiter.reset()


@dataclass
class _Wiring:
    """What the stubs saw: renders, checkpoint reopens, review requests."""

    renders: list[str]
    checkpoint_ok: bool = True
    reopens: list[str] = field(default_factory=list)
    reviews: list[str] = field(default_factory=list)


def _wire(monkeypatch: pytest.MonkeyPatch, *, render_ok: bool = True) -> _Wiring:
    renders = install_renders(monkeypatch)
    wiring = _Wiring(renders=renders)

    async def _reopen(_self: object, project_id: str) -> bool:
        wiring.reopens.append(project_id)
        return wiring.checkpoint_ok

    async def _reviewed(_self: object, project_id: str) -> None:
        wiring.reviews.append(project_id)

    async def _failing_render(_self: object, project_id: str) -> tuple[str, ...]:
        renders.append(project_id)
        return ("render_failed",)

    monkeypatch.setattr(review_reopen.CheckpointEngineReopener, "reopen", _reopen)
    monkeypatch.setattr(SessionCoverReviewHold, "reopened", _reviewed)
    if not render_ok:
        monkeypatch.setattr(
            carousel_owner_autofix.RepublishRenderer, "render", _failing_render
        )
    return wiring


@dataclass(frozen=True)
class _Seeded:
    project_id: str
    first: str
    second: str


async def _approved(client: AsyncClient) -> _Seeded:
    first = await upload_photo(client, RED)
    second = await upload_photo(client, BLUE)
    project_id = await project(client, first["id"])
    await set_project(project_id, **_APPROVED)
    return _Seeded(project_id=project_id, first=first["id"], second=second["id"])


async def _model(project_id: str) -> CarouselProjectModel:
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        return model


async def _assert_reopened(seeded: _Seeded) -> None:
    model = await _model(seeded.project_id)
    assert model.hook_asset_id == seeded.second
    assert model.workflow_status == "draft"
    assert (model.current_phase, model.phase_status) == (
        "final_review",
        "awaiting_human",
    )
    assert model.lock_version == 5


async def _assert_untouched(seeded: _Seeded) -> None:
    model = await _model(seeded.project_id)
    assert model.hook_asset_id == seeded.first
    assert model.workflow_status == "approved_for_publish"
    assert model.phase_status == "approved"
    assert model.needs_republish_since is None
    assert model.lock_version == 4


@pytest.mark.integration
async def test_a_pick_reopens_the_review_and_asks_for_a_new_one(
    client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """200 with ``review_reopened``; the run is asked for a new review."""
    # Scenario: A cover switch reopens the review of an approved carousel
    wiring = _wire(monkeypatch)
    seeded = await _approved(client)

    response = await client.put(
        f"/api/carousels/{seeded.project_id}/cover",
        json={"asset_id": seeded.second, "expected_version": 4},
    )

    assert response.status_code == 200, response.text
    assert response.json()["review_reopened"] is True
    await _assert_reopened(seeded)
    assert wiring.renders == [seeded.project_id]
    assert wiring.reopens == [seeded.project_id]
    assert wiring.reviews == [seeded.project_id]


@pytest.mark.integration
async def test_a_checkpoint_that_cannot_reopen_writes_nothing(
    client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """409: the row and the checkpoint never disagree."""
    # Scenario: A switch that cannot reopen the review refuses an approved carousel
    wiring = _wire(monkeypatch)
    wiring.checkpoint_ok = False
    seeded = await _approved(client)

    response = await client.put(
        f"/api/carousels/{seeded.project_id}/cover",
        json={"asset_id": seeded.second, "expected_version": 4},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ERR_COVER_SWITCH_REQUIRES_REVIEW
    await _assert_untouched(seeded)
    assert wiring.renders == []
    assert wiring.reviews == []


@pytest.mark.integration
async def test_a_failed_render_still_asks_for_a_new_review(
    client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The approval was dropped, so the run is asked for a review even though
    the route reports the render failure (the worker waits for a render)."""
    # Scenario: The new Telegram review waits for the render
    wiring = _wire(monkeypatch, render_ok=False)
    seeded = await _approved(client)

    response = await client.put(
        f"/api/carousels/{seeded.project_id}/cover",
        json={"asset_id": seeded.second, "expected_version": 4},
    )

    assert response.status_code >= 400
    assert (await _model(seeded.project_id)).workflow_status == "draft"
    assert wiring.reviews == [seeded.project_id]


@pytest.mark.integration
async def test_a_hook_photo_switches_renders_then_asks_for_a_review(
    client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Through the cover switch: CAS bump, one commit, the render, the hook."""
    # Scenario: A cover switch reopens the review of an approved carousel
    wiring = _wire(monkeypatch)
    seeded = await _approved(client)

    response = await client.put(
        f"/api/carousels/{seeded.project_id}/hook-photo",
        json={"creator_asset_id": seeded.second},
    )

    assert response.status_code == 200, response.text
    await _assert_reopened(seeded)
    assert (await _model(seeded.project_id)).needs_republish_since is None
    assert wiring.renders == [seeded.project_id]
    assert wiring.reviews == [seeded.project_id]


@pytest.mark.integration
async def test_an_unknown_hook_photo_writes_nothing(
    client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The photo is validated before anything is written or reopened."""
    # Scenario: A switch that cannot reopen the review refuses an approved carousel
    wiring = _wire(monkeypatch)
    seeded = await _approved(client)

    response = await client.put(
        f"/api/carousels/{seeded.project_id}/hook-photo",
        json={"creator_asset_id": str(uuid4())},
    )

    assert response.status_code == 400
    await _assert_untouched(seeded)
    assert wiring.reopens == []
    assert wiring.reviews == []
