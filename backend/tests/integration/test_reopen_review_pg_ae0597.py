"""Reopening an approved carousel's review, on Postgres.

Feature: tests/features/reopen_review_on_cover_switch_ae0597.feature. The
real picker and website switch (project lock, lock-version CAS, ``FOR
UPDATE``), the real autopilot hook, due sweep and release; the render is
recorded and the checkpoint reopen is recorded. Skipped without a Postgres
``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from rag_backend.domain.constants.carousel_autofix import AUTOFIX_STATUS_FIXED
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.autopilot import cover_review_hold
from rag_backend.modules.autopilot.cover_constants import (
    REASON_COVER_REVIEW_REOPENED,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.owner_ports import ReleaseCommand
from rag_backend.modules.autopilot.infrastructure.carousel_release import (
    PublishingCarouselReleaser,
)
from rag_backend.modules.autopilot.schedule_constants import (
    REASON_SCHEDULE_DUE,
    REASON_SCHEDULE_WITHDRAWN,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.reopen_review_pg_support import (
    APPROVED,
    Checkpoint,
    CommittedRow,
    committed,
    pick,
    run_row,
    seed_kept_run,
    sweep,
    sweep_tables,
)
from tests.integration.website_cover_review_pg_support import (
    harness,
    row,
    seed,
    seed_run,
    website_task,
)

_S = AutopilotRunState


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "out"))
    get_settings.cache_clear()
    yield assets
    get_settings.cache_clear()


def _reopened(photo: str) -> CommittedRow:
    return CommittedRow(
        workflow_status="draft",
        phase_status="awaiting_human",
        hook_asset_id=photo,
        marked=False,
        is_public=False,
    )


@requires_postgres
@pytest.mark.asyncio
async def test_a_pick_on_a_scheduled_carousel_reopens_it_in_one_commit(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing is committed before the one commit: the reopen sees the old,
    approved row; the render sees slide 1, the marker and the draft together."""
    # Scenario: A cover switch reopens the review of an approved carousel
    # Scenario: A reopened scheduled run keeps its time and gets a new review
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs, **APPROVED)
        kept = datetime.now(UTC) + timedelta(hours=4)
        await seed_kept_run(built, project_id, _S.SCHEDULED, kept)
        checkpoint = Checkpoint(built)

        result = await pick(built, project_id, photos[1], checkpoint)
        if result.reopened:
            await cover_review_hold().reopened(project_id)

        assert (result.status, result.reopened) == (AUTOFIX_STATUS_FIXED, True)
        assert checkpoint.reopened == [project_id]
        assert checkpoint.seen == [
            CommittedRow(
                workflow_status="approved_for_publish",
                phase_status="approved",
                hook_asset_id=photos[0],
                marked=False,
                is_public=False,
            )
        ]
        assert await committed(built, project_id) == _reopened(photos[1])
        assert (await row(built, project_id)).lock_version == 4
        assert len(built.renders) == 1
        run = await run_row(built, project_id)
        assert (run.state, run.reason) == (
            _S.REWORKING.value,
            REASON_COVER_REVIEW_REOPENED,
        )
        assert run.scheduled_at == kept


@requires_postgres
@pytest.mark.asyncio
async def test_a_website_cover_reopens_a_scheduled_carousel(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The website generation switches an approved carousel and asks the
    scheduled run for a new review; its time is kept."""
    # Scenario: A cover switch reopens the review of an approved carousel
    # Scenario: A reopened scheduled run keeps its time and gets a new review
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs, **APPROVED)
        kept = datetime.now(UTC) + timedelta(hours=4)
        await seed_kept_run(built, project_id, _S.SCHEDULED, kept)
        checkpoint = Checkpoint(built)

        await (await website_task(built, project_id, photos[0], checkpoint))()

        model = await row(built, project_id)
        assert model.slide_cover is not None
        assert model.slide_cover["kind"] == "ai_image"
        assert model.workflow_status == "draft"
        assert model.phase_status == "awaiting_human"
        assert checkpoint.reopened == [project_id]
        run = await run_row(built, project_id)
        assert run.state == _S.REWORKING.value
        assert run.scheduled_at == kept


@requires_postgres
@pytest.mark.asyncio
async def test_a_website_cover_on_a_cancelled_schedule_holds_then_resends(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Approved and waiting for the owner (a cancelled schedule): the website
    hold takes the review, the release leaves the run for the worker's stop."""
    # Scenario: A cover switch reopens the review of an approved carousel
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs, **APPROVED)
        await seed_run(built, project_id, _S.AWAITING_OWNER)
        checkpoint = Checkpoint(built)

        await (await website_task(built, project_id, photos[0], checkpoint))()

        assert (await row(built, project_id)).workflow_status == "draft"
        run = await run_row(built, project_id)
        assert run.state == _S.REWORKING.value
        assert built.renders and built.renders[0] is not None
        assert built.renders[0].state == _S.REWORKING.value


@requires_postgres
@pytest.mark.asyncio
async def test_a_passed_kept_time_expires_at_the_due_tick(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reopened run still waiting when its time comes: expired, not released."""
    # Scenario: A slot that passes while the review waits does not publish
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, _photos = await seed(built, dirs)
        past = datetime.now(UTC) - timedelta(minutes=1)
        await seed_kept_run(built, project_id, _S.AWAITING_OWNER, past)

        assert await sweep(built) == 1

        run = await run_row(built, project_id)
        assert (run.state, run.reason) == (
            _S.EXPIRED.value,
            REASON_SCHEDULE_WITHDRAWN,
        )
        assert (await row(built, project_id)).is_public is False


@requires_postgres
@pytest.mark.asyncio
async def test_a_kept_time_approved_on_the_website_publishes(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Approved again on the website before its time: released at that time."""
    # Scenario: A kept time approved again on the website publishes at its time
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, _photos = await seed(built, dirs, **APPROVED)
        past = datetime.now(UTC) - timedelta(minutes=1)
        await seed_kept_run(built, project_id, _S.AWAITING_OWNER, past)

        assert await sweep(built) == 1

        run = await run_row(built, project_id)
        assert (run.state, run.reason) == (_S.PUBLISHING.value, REASON_SCHEDULE_DUE)
        assert (await row(built, project_id)).is_public is True


@requires_postgres
@pytest.mark.asyncio
async def test_a_kept_time_still_ahead_is_not_due(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reopened run whose time is ahead waits; nothing moves."""
    # Scenario: A reopened scheduled run keeps its time and gets a new review
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, _photos = await seed(built, dirs)
        ahead = datetime.now(UTC) + timedelta(hours=2)
        await seed_kept_run(built, project_id, _S.AWAITING_OWNER, ahead)

        assert await sweep(built) == 0
        assert (await run_row(built, project_id)).state == _S.AWAITING_OWNER.value


@requires_postgres
@pytest.mark.asyncio
async def test_a_release_refuses_a_reopened_carousel(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``Publicar agora`` or an approve's release on a draft: nothing released."""
    # Scenario: A release never publishes a carousel whose approval was dropped
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, _photos = await seed(built, dirs)

        async with built.sessions()() as session:
            released = await PublishingCarouselReleaser(session).release(
                ReleaseCommand(project_id=project_id)
            )

        assert released is False
        assert (await row(built, project_id)).is_public is False


@requires_postgres
@pytest.mark.asyncio
async def test_an_approved_carousel_is_still_released(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The release still works for an approved carousel."""
    # Scenario: A release never publishes a carousel whose approval was dropped
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, _photos = await seed(built, dirs, **APPROVED)

        async with built.sessions()() as session:
            released = await PublishingCarouselReleaser(session).release(
                ReleaseCommand(project_id=project_id)
            )

        assert released is True
        assert (await row(built, project_id)).is_public is True
