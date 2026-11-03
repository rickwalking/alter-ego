"""Website cover switches that must not land, or must be undone, on Postgres.

Feature: tests/features/website_cover_review_switch_ae0594.feature. The real
generation, selection, review-switch store, run repository and review hold
(see ``website_cover_review_pg_support``); the bridge is a fake editor and the
render is recorded. Skipped without a Postgres ``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverWrite,
    CoverBaseline,
)
from rag_backend.domain.constants.cover_autoselect import (
    LOG_COVER_AUTO_SELECT,
    REASON_AUTO_SELECT_ASSET_GONE,
    REASON_AUTO_SELECT_COMPLETED,
    REASON_AUTO_SELECT_NO_PROJECT,
)
from rag_backend.domain.constants.cover_review_switch import (
    REASON_AUTO_SELECT_APPROVED,
    REASON_AUTO_SELECT_PUBLISHED,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.editorial.infrastructure.carousel_cover_generation import (
    EditorialGeneratedCovers,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_review_switch import (
    EditorialReviewCoverStore,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.website_cover_review_pg_support import (
    Harness,
    RunFacts,
    autopilot_task,
    harness,
    result_asset,
    row,
    run_facts,
    seed,
    seed_run,
    tables,
    website_task,
)

_AWAITING = AutopilotRunState.AWAITING_OWNER
_RenderAnswer = Callable[[Harness, str, int], Awaitable[tuple[str, ...]]]


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "out"))
    get_settings.cache_clear()
    yield assets
    get_settings.cache_clear()


def _skips(logs: list[dict[str, object]]) -> list[object]:
    return [e["reason"] for e in logs if e["event"] == LOG_COVER_AUTO_SELECT]


async def _assert_unchanged(built: Harness, project_id: str, photo: str) -> None:
    model = await row(built, project_id)
    assert model.slide_cover is None
    assert model.hook_asset_id == photo
    assert model.lock_version == 3
    assert built.renders == []


@requires_postgres
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("values", "state"),
    [
        ({"workflow_status": "approved_for_publish"}, None),
        ({"workflow_status": "approved_for_publish"}, AutopilotRunState.SCHEDULED),
    ],
)
async def test_website_cover_on_an_approved_carousel_is_an_option(
    dirs: Path,
    monkeypatch: pytest.MonkeyPatch,
    values: dict[str, object],
    state: AutopilotRunState | None,
) -> None:
    """Approved or scheduled, no checkpoint reopen wired: slide 1 unchanged, the
    cover offered, the run kept."""
    # Scenario: A switch that cannot reopen the review refuses an approved carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs, **values)
        if state is not None:
            await seed_run(built, project_id, state)

        with capture_logs() as logs:
            await (await website_task(built, project_id, photos[0]))()

        await _assert_unchanged(built, project_id, photos[0])
        assert _skips(logs) == [REASON_AUTO_SELECT_APPROVED]
        asset = await result_asset(built, project_id)
        async with built.sessions()() as session:
            offered = await EditorialGeneratedCovers(session).covers(project_id)
        assert [str(item.id) for item in offered] == [asset]
        facts = await run_facts(built, project_id)
        if state is not None:
            assert facts == RunFacts(state=state.value, reason=None, rework_phase=None)


@requires_postgres
@pytest.mark.asyncio
async def test_website_cover_on_a_published_carousel_is_an_option(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Released: slide 1 unchanged and the skip reason is carousel_published."""
    # Scenario: A website cover on a published carousel stays a picker option
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(
            built, dirs, workflow_status="approved_for_publish", is_public=True
        )
        await seed_run(built, project_id, AutopilotRunState.PUBLISHED)

        with capture_logs() as logs:
            await (await website_task(built, project_id, photos[0]))()

        await _assert_unchanged(built, project_id, photos[0])
        assert _skips(logs) == [REASON_AUTO_SELECT_PUBLISHED]
        assert built.instagram == []


@requires_postgres
@pytest.mark.asyncio
async def test_autopilot_cover_on_a_completed_carousel_is_unchanged(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An autopilot-started generation still skips a completed carousel."""
    # Scenario: An autopilot cover on a completed carousel is unchanged
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        await seed_run(built, project_id, _AWAITING)

        with capture_logs() as logs:
            await (await autopilot_task(built, project_id, photos[0]))()

        await _assert_unchanged(built, project_id, photos[0])
        assert _skips(logs) == [REASON_AUTO_SELECT_COMPLETED]
        assert await run_facts(built, project_id) == RunFacts(
            state=_AWAITING.value, reason=None, rework_phase=None
        )


@requires_postgres
@pytest.mark.asyncio
async def test_review_store_refuses_gone_rows_and_assets(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unknown project or asset writes nothing."""
    # Scenario: A website cover switches a completed carousel in final review
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        store = EditorialReviewCoverStore(built.sessions())
        baseline = CoverBaseline(
            slide_cover_asset_id=None, hook_asset_id=UUID(photos[0])
        )

        def _write(target: str, asset: UUID) -> AutoCoverWrite:
            return AutoCoverWrite(
                project_id=target,
                asset_id=asset,
                expected_version=3,
                baseline=baseline,
            )

        gone = await store.switch_in_review(_write(str(uuid4()), uuid4()))
        assert gone.status == REASON_AUTO_SELECT_NO_PROJECT
        missing = await store.switch_in_review(_write(project_id, uuid4()))
        assert missing.status == REASON_AUTO_SELECT_ASSET_GONE
        await _assert_unchanged(built, project_id, photos[0])
