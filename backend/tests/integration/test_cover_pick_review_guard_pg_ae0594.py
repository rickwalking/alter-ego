"""The picker refuses an approved, scheduled or published carousel, on Postgres.

Feature: tests/features/website_cover_review_switch_ae0594.feature. The real
picker (``cover_pick_service``: library, generated covers, the cover switch
and the editorial approval read); the render is recorded. Skipped without a
Postgres ``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest

from rag_backend.application.services.carousel.cover_pick import (
    CoverPickCommand,
    CoverPickError,
)
from rag_backend.domain.constants.carousel_autofix import AUTOFIX_STATUS_FIXED
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_SWITCH_REQUIRES_REVIEW,
)
from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.editorial.public import (
    CarouselAutomationAcl,
    cover_pick_service,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.website_cover_review_pg_support import (
    Harness,
    harness,
    row,
    seed,
    seed_run,
    tables,
)

_APPROVED = {"workflow_status": "approved_for_publish"}


class _NoOffer:
    async def offer(self, project_id: str) -> SlideCover | None:
        del project_id
        return None


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "out"))
    get_settings.cache_clear()
    yield assets
    get_settings.cache_clear()


async def _pick(built: Harness, project_id: str, photo: str) -> str:
    """Pick library photo ``photo`` at the seeded lock version."""
    async with built.sessions()() as session:
        project = await CarouselAutomationAcl(session).load_project(project_id)
        assert project is not None
        result = await cover_pick_service(session, _NoOffer()).pick(
            CoverPickCommand(
                project=project,
                asset_id=UUID(photo),
                expected_version=3,
            )
        )
    return result.status


async def _refused(built: Harness, project_id: str, photos: list[str]) -> None:
    with pytest.raises(CoverPickError) as refused:
        await _pick(built, project_id, photos[1])
    assert refused.value.code == ERR_COVER_SWITCH_REQUIRES_REVIEW
    model = await row(built, project_id)
    assert model.hook_asset_id == photos[0]
    assert model.slide_cover is None
    assert model.lock_version == 3
    assert built.renders == []


@requires_postgres
@pytest.mark.asyncio
async def test_picker_refuses_an_approved_carousel(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Approved for publishing: refused, nothing written or rendered."""
    # Scenario: The picker refuses an approved carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs, **_APPROVED)

        await _refused(built, project_id, photos)


@requires_postgres
@pytest.mark.asyncio
async def test_picker_refuses_a_scheduled_carousel(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An autopilot run waiting for its publish time: refused."""
    # Scenario: The picker refuses a scheduled carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs, **_APPROVED)
        await seed_run(built, project_id, AutopilotRunState.SCHEDULED)

        await _refused(built, project_id, photos)


@requires_postgres
@pytest.mark.asyncio
async def test_picker_refuses_a_published_carousel(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Released: refused, the public slides never change."""
    # Scenario: The picker refuses a published carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs, is_public=True)

        await _refused(built, project_id, photos)


@requires_postgres
@pytest.mark.asyncio
async def test_picker_still_switches_a_carousel_in_review(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Waiting for its first approval: the pick switches and re-renders."""
    # Scenario: The picker refuses an approved carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)

        assert await _pick(built, project_id, photos[1]) == AUTOFIX_STATUS_FIXED

        model = await row(built, project_id)
        assert model.hook_asset_id == photos[1]
        assert model.lock_version == 4
        assert built.renders == [None]
