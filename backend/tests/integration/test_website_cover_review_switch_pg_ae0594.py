"""A website cover switches a completed carousel in final review, on Postgres.

Feature: tests/features/website_cover_review_switch_ae0594.feature. The real
generation, selection, review-switch store, run repository and review hold
(see ``website_cover_review_pg_support``); the bridge is a fake editor and the
render is recorded. Skipped without a Postgres ``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import update
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverSelection,
    CoverBaseline,
)
from rag_backend.application.services.carousel.cover_review_switch import (
    ReviewSwitch,
)
from rag_backend.domain.constants.cover_autoselect import (
    LOG_COVER_AUTO_SELECT,
    OUTCOME_AUTO_SELECT_ALREADY,
    REASON_AUTO_SELECT_CONFLICT,
    REASON_AUTO_SELECT_MANUAL_CHOICE,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.cover_constants import (
    COVER_REVIEW_HOLD_PHASE,
    REASON_COVER_REVIEW_HOLD,
    REASON_COVER_REVIEW_KEPT,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.editorial.infrastructure.carousel_cover_autoselect import (
    auto_cover_selector,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_review_switch import (
    EditorialReviewCoverStore,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_lock import (
    carousel_project_lock,
)
from rag_backend.modules.editorial.public import CarouselProjectWriteOwner
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.website_cover_review_pg_support import (
    Harness,
    RunFacts,
    harness,
    result_asset,
    row,
    run_facts,
    run_updated_at,
    seed,
    seed_run,
    tables,
    website_task,
)
from tests.unit.application.cover_review_fakes import NoReviewHold

_AWAITING = AutopilotRunState.AWAITING_OWNER


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
async def test_website_cover_switches_and_stays_in_final_review(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cover is stored, the slides re-rendered, the review left open."""
    # Scenario: A website cover switches a completed carousel in final review
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)

        await (await website_task(built, project_id, photos[0]))()

        asset = await result_asset(built, project_id)
        model = await row(built, project_id)
        assert asset is not None
        assert isinstance(model.slide_cover, dict)
        assert model.slide_cover["asset_id"] == asset
        assert model.slide_cover["kind"] == "ai_image"
        assert model.hook_asset_id == photos[0]
        assert model.lock_version == 4
        assert built.renders == [None]
        assert model.status == "completed"
        assert model.current_phase == "final_review"
        assert model.phase_status == "awaiting_human"
        assert model.workflow_status == "draft"
        assert model.is_public is False
        assert built.instagram == []


@requires_postgres
@pytest.mark.asyncio
async def test_website_approval_read_before_the_switch_is_refused(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The review page's lock version no longer matches: the approve CAS refuses."""
    # Scenario: A website approval read before the switch is refused
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        await (await website_task(built, project_id, photos[0]))()

        async with built.sessions()() as session:
            owner = CarouselProjectWriteOwner(session)
            with pytest.raises(ValueError, match=ERR_VERSION_CONFLICT):
                await owner.bump_resume_lock_version(project_id, 3)
            await session.rollback()
            assert await owner.bump_resume_lock_version(project_id, 4) == 5


@requires_postgres
@pytest.mark.asyncio
async def test_telegram_review_is_held_while_slide_one_changes(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The run leaves awaiting_owner before the render; the worker re-sends it."""
    # Scenario: The Telegram review is held while slide 1 changes
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        await seed_run(built, project_id, _AWAITING)

        await (await website_task(built, project_id, photos[0]))()

        held = RunFacts(
            state=AutopilotRunState.REWORKING.value,
            reason=REASON_COVER_REVIEW_HOLD,
            rework_phase=COVER_REVIEW_HOLD_PHASE,
        )
        assert built.renders == [held]
        after = await run_facts(built, project_id)
        assert after == RunFacts(
            state=AutopilotRunState.REWORKING.value,
            reason=REASON_COVER_REVIEW_HOLD,
            rework_phase=None,
        )
        assert (await row(built, project_id)).lock_version == 4


def _owner_write_after_recheck(
    monkeypatch: pytest.MonkeyPatch, built: Harness, values: dict[str, object]
) -> None:
    """Commit ``values`` from another session between the re-check and the write."""
    from rag_backend.modules.editorial.infrastructure import (
        carousel_cover_review_switch,
    )

    original = carousel_cover_review_switch._stage

    async def _stage_then_owner_write(
        session: object, target: tuple[object, object]
    ) -> bool:
        project_id = str(target[0].id)
        async with built.sessions()() as other:
            await other.execute(
                update(CarouselProjectModel)
                .where(CarouselProjectModel.id == project_id)
                .values(**values)
            )
            await other.commit()
        return await original(session, target)

    monkeypatch.setattr(carousel_cover_review_switch, "_stage", _stage_then_owner_write)


@requires_postgres
@pytest.mark.asyncio
async def test_owner_choice_while_the_job_ran_wins(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An owner photo committed before the locked write is kept, the run handed back."""
    # Scenario: A cover the owner chose while the job ran wins on a completed carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        await seed_run(built, project_id, _AWAITING)
        task = await website_task(built, project_id, photos[0])
        _owner_write_after_recheck(monkeypatch, built, {"hook_asset_id": photos[1]})

        with capture_logs() as logs:
            await task()

        model = await row(built, project_id)
        assert model.hook_asset_id == photos[1]
        assert model.slide_cover is None
        assert model.lock_version == 3
        assert built.renders == []
        assert _skips(logs) == [REASON_AUTO_SELECT_MANUAL_CHOICE]
        assert await run_facts(built, project_id) == RunFacts(
            state=_AWAITING.value, reason=REASON_COVER_REVIEW_KEPT, rework_phase=None
        )


@requires_postgres
@pytest.mark.asyncio
async def test_photo_bound_before_the_selection_read_is_kept(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A change since the baseline is a manual choice before any hold."""
    # Scenario: A cover the owner chose while the job ran wins on a completed carousel
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        await seed_run(built, project_id, _AWAITING)
        task = await website_task(built, project_id, photos[0])
        async with built.sessions()() as session:
            await session.execute(
                update(CarouselProjectModel)
                .where(CarouselProjectModel.id == project_id)
                .values(hook_asset_id=photos[1])
            )
            await session.commit()

        with capture_logs() as logs:
            await task()

        assert _skips(logs) == [REASON_AUTO_SELECT_MANUAL_CHOICE]
        assert (await row(built, project_id)).slide_cover is None
        assert built.renders == []
        assert await run_facts(built, project_id) == RunFacts(
            state=_AWAITING.value, reason=None, rework_phase=None
        )


@requires_postgres
@pytest.mark.asyncio
async def test_held_lock_on_a_completed_carousel_is_a_logged_skip(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Another holder of the project lock: nothing written, the run handed back."""
    # Scenario: A lock conflict on a completed carousel is skipped and logged
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        await seed_run(built, project_id, _AWAITING)
        anchor = await run_updated_at(built, project_id)
        task = await website_task(built, project_id, photos[0])

        with capture_logs() as logs:
            async with carousel_project_lock(engine, project_id, blocking=False):
                await task()

        await _assert_unchanged(built, project_id, photos[0])
        assert _skips(logs) == [REASON_AUTO_SELECT_CONFLICT]
        assert await run_facts(built, project_id) == RunFacts(
            state=_AWAITING.value, reason=REASON_COVER_REVIEW_KEPT, rework_phase=None
        )
        assert await run_updated_at(built, project_id) == anchor


@requires_postgres
@pytest.mark.asyncio
async def test_failed_website_generation_leaves_the_carousel_alone(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bridge failure never selects, holds or renders."""
    # Scenario: A failed website generation leaves a completed carousel alone
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        await seed_run(built, project_id, _AWAITING)
        built.editor.error = RuntimeError("grok refused")

        with capture_logs() as logs:
            await (await website_task(built, project_id, photos[0]))()

        assert await result_asset(built, project_id) is None
        await _assert_unchanged(built, project_id, photos[0])
        assert _skips(logs) == []
        assert await run_facts(built, project_id) == RunFacts(
            state=_AWAITING.value, reason=None, rework_phase=None
        )


@requires_postgres
@pytest.mark.asyncio
async def test_replaying_the_success_changes_nothing(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same success again is already_selected: no write, no render, no hold."""
    # Scenario: Replaying a website cover success changes nothing
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        await (await website_task(built, project_id, photos[0]))()
        from rag_backend.modules.editorial.infrastructure.cover_generations import (
            SqlCoverGenerationRepository,
        )

        async with built.sessions()() as session:
            generations = await SqlCoverGenerationRepository(session).for_project(
                project_id
            )
        selection = AutoCoverSelection(
            project_id=project_id,
            generation_id=generations[0].id,
            baseline=CoverBaseline(
                slide_cover_asset_id=None, hook_asset_id=UUID(photos[0])
            ),
            review=ReviewSwitch(
                store=EditorialReviewCoverStore(built.sessions()), hold=NoReviewHold()
            ),
        )

        outcome = await auto_cover_selector().select(selection)

        assert outcome == OUTCOME_AUTO_SELECT_ALREADY
        assert (await row(built, project_id)).lock_version == 4
        assert built.renders == [None]
