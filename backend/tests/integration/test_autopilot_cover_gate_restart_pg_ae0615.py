"""The autopilot cover survives a worker restart, on Postgres.

Feature: The autopilot puts its succeeded cover on slide 1 at the next gate
(tests/features/autopilot_cover_gate_select_ae0615.feature). A restart (a
deploy) ends the background wait without a read and loads the gate module
afresh, so no process memory survives it; the gates then find the cover and
the owner-choice baseline in the database. The baseline row is written in the
generation's own transaction, so a failed write leaves no pending generation.
Skipped without a Postgres ``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverSelection,
    AutoCoverSelector,
    CoverBaseline,
)
from rag_backend.domain.constants.cover_autoselect import (
    REASON_AUTO_SELECT_MANUAL_CHOICE,
    REASON_AUTO_SELECT_TIMED_OUT,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.editorial.infrastructure import carousel_cover_gate_select
from rag_backend.modules.editorial.infrastructure.carousel_cover_autostart import (
    schedule_autopilot_cover,
)
from rag_backend.modules.editorial.infrastructure.cover_generations import (
    SqlCoverGenerationRepository,
)
from tests.integration.cover_gate_pg_support import (
    _GATES,
    Task,
    _Drive,
    _reasons,
    _running_research,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.test_autopilot_cover_autoselect_pg_ae0590 import (
    _harness,
    _result_asset,
    _row,
    _start,
)
from tests.integration.test_autopilot_cover_autostart_pg_ae0581 import _tables


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "out"))
    get_settings.cache_clear()
    yield assets
    get_settings.cache_clear()


def _deploy_kills_the_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """The background wait ends without a read: the process it ran in is gone."""

    async def _gone(_self: AutoCoverSelector, _selection: AutoCoverSelection) -> str:
        return REASON_AUTO_SELECT_TIMED_OUT

    monkeypatch.setattr(AutoCoverSelector, "select", _gone)


async def _succeed_then_restart(
    harness_task: Task, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cover succeeds, then a deploy restarts the worker: the gate module is
    loaded afresh, so nothing the old process held in memory survives."""
    with monkeypatch.context() as during:
        _deploy_kills_the_wait(during)
        await harness_task()
    importlib.reload(carousel_cover_gate_select)


@pytest.mark.asyncio
async def test_restart_after_the_cover_succeeded_still_shows_it(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deploy between the cover and the next gate: the first review has it."""
    # Scenario: A restart before the next gate still shows the cover
    async with isolated_schema(_tables()) as engine:
        project_id, photos = await _running_research(engine, dirs)
        harness = _harness(engine, monkeypatch)
        task = await _start(harness, project_id)
        await _succeed_then_restart(task, monkeypatch)
        drive = _Drive(engine=engine, project_id=project_id)

        await drive.sleep(0.0)

        asset = await _result_asset(engine, project_id)
        row = await _row(engine, project_id)
        assert asset is not None
        assert isinstance(row.slide_cover, dict)
        assert row.slide_cover["asset_id"] == asset
        assert row.slide_cover["kind"] == "ai_image"
        assert row.hook_asset_id == photos[0]
        assert row.lock_version == 4
        assert drive.applied == [(gate, gate == "research") for gate in _GATES]


@requires_postgres
@pytest.mark.asyncio
async def test_owner_pick_across_a_restart_is_kept(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The baseline survives the restart: the owner's later photo wins."""
    # Scenario: An owner's pick made after scheduling is kept across a restart
    async with isolated_schema(_tables()) as engine:
        project_id, photos = await _running_research(engine, dirs)
        harness = _harness(engine, monkeypatch)
        task = await _start(harness, project_id)
        await _succeed_then_restart(task, monkeypatch)
        drive = _Drive(
            engine=engine, project_id=project_id, before={"hook_asset_id": photos[1]}
        )

        with capture_logs() as logs:
            await drive.sleep(0.0)

        row = await _row(engine, project_id)
        assert row.slide_cover is None
        assert row.hook_asset_id == photos[1]
        assert row.lock_version == 3
        assert drive.applied == [(gate, False) for gate in _GATES]
        assert set(_reasons(logs)) == {REASON_AUTO_SELECT_MANUAL_CHOICE}


class _BaselineTableMissingError(RuntimeError):
    """The baseline write fails (a worker started before the new table exists)."""


@requires_postgres
@pytest.mark.asyncio
async def test_failed_baseline_write_leaves_no_pending_generation(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The generation row and its baseline are one commit: both or neither."""
    # Scenario: A failed baseline write leaves no stuck generation
    async with isolated_schema(_tables()) as engine:
        project_id, _ = await _running_research(engine, dirs)
        harness = _harness(engine, monkeypatch)

        async def _fails(
            _self: SqlCoverGenerationRepository,
            _generation_id: UUID,
            _baseline: CoverBaseline,
        ) -> None:
            raise _BaselineTableMissingError

        monkeypatch.setattr(
            SqlCoverGenerationRepository, "record_autopilot_baseline", _fails
        )
        factory = async_sessionmaker(engine, expire_on_commit=False)

        with pytest.raises(_BaselineTableMissingError):
            async with factory() as session:
                await schedule_autopilot_cover(session, project_id)

        async with factory() as session:
            rows = await SqlCoverGenerationRepository(session).for_project(project_id)
        assert rows == ()
        assert harness.tasks == []
