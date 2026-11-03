"""A reopened run left in ``reworking`` never waits forever, on Postgres.

Feature: tests/features/reopen_review_on_cover_switch_ae0597.feature. Both
ways a run reaches ``reworking`` with a kept time (a switch on a scheduled
carousel, and the due tick's recovery after a slow schedule tap), then the
owner approves on the website, or not at all. When the kept time comes the
real due sweep publishes the approved carousel or expires the run
(``schedule_withdrawn``). The worker's own hand-back of an approved run is
covered by the policy and runner unit tests. Skipped without a Postgres
``DATABASE_URL``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import update

from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.schedule_constants import (
    REASON_SCHEDULE_DUE,
    REASON_SCHEDULE_WITHDRAWN,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.reopen_review_pg_support import (
    APPROVED,
    Checkpoint,
    age_run,
    run_row,
    seed_kept_run,
    sweep,
    sweep_tables,
)
from tests.integration.website_cover_review_pg_support import (
    Harness,
    harness,
    row,
    seed,
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


async def _approve_on_the_website(built: Harness, project_id: str) -> None:
    async with built.sessions()() as session:
        await session.execute(
            update(CarouselProjectModel)
            .where(CarouselProjectModel.id == project_id)
            .values(**APPROVED)
        )
        await session.commit()


async def _time_comes(built: Harness, project_id: str) -> None:
    async with built.sessions()() as session:
        await session.execute(
            update(AutopilotRunModel)
            .where(AutopilotRunModel.carousel_project_id == project_id)
            .values(scheduled_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await session.commit()


async def _switched(built: Harness, dirs: Path) -> str:
    """A switch on a scheduled carousel: the run is ``reworking``, time kept."""
    project_id, photos = await seed(built, dirs, **APPROVED)
    kept = datetime.now(UTC) + timedelta(hours=4)
    await seed_kept_run(built, project_id, _S.SCHEDULED, kept)
    await (await website_task(built, project_id, photos[0], Checkpoint(built)))()
    assert (await run_row(built, project_id)).state == _S.REWORKING.value
    return project_id


async def _recovered(built: Harness, dirs: Path) -> str:
    """A schedule tap slower than the grace: the recovery moved the run."""
    project_id, _photos = await seed(built, dirs)
    kept = datetime.now(UTC) + timedelta(hours=4)
    await seed_kept_run(built, project_id, _S.SCHEDULED, kept)
    await age_run(built, project_id, timedelta(minutes=10))
    assert await sweep(built) == 1
    assert (await run_row(built, project_id)).state == _S.REWORKING.value
    return project_id


@requires_postgres
@pytest.mark.asyncio
@pytest.mark.parametrize("trigger", ["switch", "recovery"])
async def test_a_run_approved_on_the_website_publishes_at_its_time(
    dirs: Path, monkeypatch: pytest.MonkeyPatch, trigger: str
) -> None:
    """Approved again while ``reworking``: released when its time comes."""
    # Scenario: A run whose carousel was approved on the website goes back to the owner
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        reach = _switched if trigger == "switch" else _recovered
        project_id = await reach(built, dirs)
        await _approve_on_the_website(built, project_id)
        await _time_comes(built, project_id)

        assert await sweep(built) == 1

        run = await run_row(built, project_id)
        assert (run.state, run.reason) == (_S.PUBLISHING.value, REASON_SCHEDULE_DUE)
        assert (await row(built, project_id)).is_public is True


@requires_postgres
@pytest.mark.asyncio
@pytest.mark.parametrize("trigger", ["switch", "recovery"])
async def test_a_run_never_approved_again_expires_at_its_time(
    dirs: Path, monkeypatch: pytest.MonkeyPatch, trigger: str
) -> None:
    """Still a draft while ``reworking`` (a render that never landed, a review
    nobody answered): expired at its time, nothing released."""
    # Scenario: A run whose carousel was approved on the website goes back to the owner
    async with isolated_schema(sweep_tables()) as engine:
        built = harness(engine, monkeypatch)
        reach = _switched if trigger == "switch" else _recovered
        project_id = await reach(built, dirs)
        await _time_comes(built, project_id)

        assert await sweep(built) == 1

        run = await run_row(built, project_id)
        assert (run.state, run.reason) == (
            _S.EXPIRED.value,
            REASON_SCHEDULE_WITHDRAWN,
        )
        assert (await row(built, project_id)).is_public is False
