"""A cover switch races the scheduled-publish sweep, on Postgres.

Feature: tests/features/reopen_review_on_cover_switch_ae0597.feature. Each
side runs on its own session and takes its real locks: the sweep locks the
carousel row (``SELECT ... FOR UPDATE``) before it reads the approval and
holds it until the run move and the release commit; the switch (the picker)
takes the project lock and the lock-version CAS on the same row before it
re-reads the release and drops the approval. Either the release wins and the
switch is refused as published (slide 1 and the approval untouched), or the
switch wins and nothing is released (the run expires: its time came while the
review was reopened). Skipped without a Postgres ``DATABASE_URL``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from rag_backend.domain.constants.carousel_autofix import AUTOFIX_STATUS_FIXED
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_SWITCH_REQUIRES_REVIEW,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.owner_ports import ReleaseCommand
from rag_backend.modules.autopilot.infrastructure import schedule_store
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
    committed,
    pick,
    run_row,
    seed_kept_run,
    sweep,
    sweep_tables,
)
from tests.integration.website_cover_review_pg_support import Harness, harness, seed

_S = AutopilotRunState
_BLOCKED_SECONDS = 0.5
_WAIT_SECONDS = 15.0
_FREE_RACES = 8


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "out"))
    get_settings.cache_clear()
    yield assets
    get_settings.cache_clear()


@dataclass(frozen=True)
class _Race:
    project_id: str
    photos: list[str]


async def _due_and_approved(built: Harness, dirs: Path) -> _Race:
    """An approved carousel whose scheduled run is due now."""
    project_id, photos = await seed(built, dirs, **APPROVED)
    due = datetime.now(UTC) - timedelta(seconds=1)
    await seed_kept_run(built, project_id, _S.SCHEDULED, due)
    return _Race(project_id=project_id, photos=photos)


async def _assert_one_side_won(built: Harness, race: _Race, status: str) -> bool:
    """The invariant; True when the release won."""
    after = await committed(built, race.project_id)
    run = await run_row(built, race.project_id)
    if after.is_public:
        assert status == ERR_COVER_SWITCH_REQUIRES_REVIEW
        assert after.hook_asset_id == race.photos[0]
        assert after.workflow_status == "approved_for_publish"
        assert (run.state, run.reason) == (_S.PUBLISHING.value, REASON_SCHEDULE_DUE)
        return True
    assert status == AUTOFIX_STATUS_FIXED
    assert after.hook_asset_id == race.photos[1]
    assert after.workflow_status == "draft"
    assert after.phase_status == "awaiting_human"
    assert (run.state, run.reason) == (_S.EXPIRED.value, REASON_SCHEDULE_WITHDRAWN)
    return False


def _pausing_lock(
    monkeypatch: pytest.MonkeyPatch, locked: asyncio.Event, proceed: asyncio.Event
) -> None:
    """The sweep signals once it holds the carousel row, then waits."""
    original = schedule_store.EditorialCarouselRowLock.lock

    async def _lock(self: schedule_store.EditorialCarouselRowLock, pid: str) -> None:
        await original(self, pid)
        locked.set()
        await proceed.wait()

    monkeypatch.setattr(schedule_store.EditorialCarouselRowLock, "lock", _lock)


@requires_postgres
@pytest.mark.asyncio
async def test_the_release_wins_and_the_switch_is_refused_as_published(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The sweep holds the row: the switch waits on it, then finds it public."""
    # Scenario: The scheduled publish and a cover switch never both win
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        race = await _due_and_approved(built, dirs)
        locked, proceed = asyncio.Event(), asyncio.Event()
        _pausing_lock(monkeypatch, locked, proceed)
        checkpoint = Checkpoint(built)

        sweeping = asyncio.create_task(sweep(built))
        await asyncio.wait_for(locked.wait(), _WAIT_SECONDS)
        switching = asyncio.create_task(
            pick(built, race.project_id, race.photos[1], checkpoint)
        )
        await asyncio.sleep(_BLOCKED_SECONDS)
        assert not switching.done()
        proceed.set()
        moved, result = await asyncio.gather(sweeping, switching)

        assert moved == 1
        assert await _assert_one_side_won(built, race, result.status) is True
        assert checkpoint.reopened == []
        assert built.renders == []


@requires_postgres
@pytest.mark.asyncio
async def test_the_switch_wins_and_nothing_is_released(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The switch holds the row: the sweep waits on it, then finds a draft."""
    # Scenario: The scheduled publish and a cover switch never both win
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        race = await _due_and_approved(built, dirs)
        checkpoint = Checkpoint(built, proceed=asyncio.Event())

        switching = asyncio.create_task(
            pick(built, race.project_id, race.photos[1], checkpoint)
        )
        await asyncio.wait_for(checkpoint.entered.wait(), _WAIT_SECONDS)
        sweeping = asyncio.create_task(sweep(built))
        await asyncio.sleep(_BLOCKED_SECONDS)
        assert not sweeping.done()
        assert checkpoint.proceed is not None
        checkpoint.proceed.set()
        result, moved = await asyncio.gather(switching, sweeping)

        assert moved == 1
        assert result.reopened is True
        assert await _assert_one_side_won(built, race, result.status) is False


@requires_postgres
@pytest.mark.asyncio
async def test_a_free_race_never_publishes_an_unreviewed_cover(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unpaused, many times: every outcome is one of the two above."""
    # Scenario: The scheduled publish and a cover switch never both win
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        for _ in range(_FREE_RACES):
            race = await _due_and_approved(built, dirs)
            checkpoint = Checkpoint(built)

            moved, result = await asyncio.gather(
                sweep(built),
                pick(built, race.project_id, race.photos[1], checkpoint),
            )

            assert moved == 1
            await _assert_one_side_won(built, race, result.status)


@requires_postgres
@pytest.mark.asyncio
async def test_a_release_waiting_on_the_switch_releases_nothing(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``Publicar agora`` read the carousel approved, then the switch landed:
    the release's compare-and-set re-reads it and refuses the draft."""
    # Scenario: A release never publishes a carousel whose approval was dropped
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs, **APPROVED)
        checkpoint = Checkpoint(built, proceed=asyncio.Event())

        async def _release() -> bool:
            async with built.sessions()() as session:
                return await PublishingCarouselReleaser(session).release(
                    ReleaseCommand(project_id=project_id)
                )

        switching = asyncio.create_task(pick(built, project_id, photos[1], checkpoint))
        await asyncio.wait_for(checkpoint.entered.wait(), _WAIT_SECONDS)
        releasing = asyncio.create_task(_release())
        await asyncio.sleep(_BLOCKED_SECONDS)
        assert not releasing.done()
        assert checkpoint.proceed is not None
        checkpoint.proceed.set()
        result, released = await asyncio.gather(switching, releasing)

        assert result.status == AUTOFIX_STATUS_FIXED
        assert released is False
        after = await committed(built, project_id)
        assert (after.is_public, after.workflow_status) == (False, "draft")
