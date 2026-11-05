"""The autopilot's succeeded cover reaches slide 1 at the drive's gates, on Postgres.

Feature: The autopilot puts its succeeded cover on slide 1 at the next gate
(tests/features/autopilot_cover_gate_select_ae0615.feature). The autostart
helper, the generation run, the background selection, the asset store, the
locked write and the consent-gated scheduler are real; the image bridge is a
fake editor, the background task runs inline and the drive is simulated by the
poll's sleep (``cover_gate_pg_support._Drive``). Skipped without a Postgres
``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from rag_backend.domain.constants.cover_autoselect import (
    REASON_AUTO_SELECT_COMPLETED,
    REASON_AUTO_SELECT_MANUAL_CHOICE,
    REASON_AUTO_SELECT_OWNER_COVER,
)
from rag_backend.infrastructure.config.settings import get_settings
from tests.integration.cover_gate_pg_support import (
    _GATES,
    _Drive,
    _poll_through,
    _reasons,
    _running_research,
    _set,
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


@pytest.mark.asyncio
async def test_drive_through_to_final_review_shows_the_cover(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The prod case: no pause the poll sees, the first review still has the cover."""
    # Scenario: A drive straight through to the final review shows the cover
    # Scenario: The drive stores the cover at a gate before it resumes
    async with isolated_schema(_tables()) as engine:
        project_id, photos = await _running_research(engine, dirs)
        harness = _harness(engine, monkeypatch)
        drive = _Drive(engine=engine, project_id=project_id)
        _poll_through(monkeypatch, drive)
        task = await _start(harness, project_id)

        with capture_logs() as logs:
            await task()

        asset = await _result_asset(engine, project_id)
        row = await _row(engine, project_id)
        assert asset is not None
        assert isinstance(row.slide_cover, dict)
        assert row.slide_cover["asset_id"] == asset
        assert row.slide_cover["kind"] == "ai_image"
        assert row.hook_asset_id == photos[0]
        assert row.lock_version == 4
        assert drive.applied == [(gate, gate == "research") for gate in _GATES]
        assert _reasons(logs) == ["", "", "", "", "", REASON_AUTO_SELECT_COMPLETED]


@requires_postgres
@pytest.mark.asyncio
async def test_owner_photo_bound_before_the_gate_is_kept(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A slide-1 photo bound after scheduling wins over the generated cover."""
    # Scenario: The owner's photo chosen before the gate is kept
    async with isolated_schema(_tables()) as engine:
        project_id, photos = await _running_research(engine, dirs)
        harness = _harness(engine, monkeypatch)
        drive = _Drive(
            engine=engine, project_id=project_id, before={"hook_asset_id": photos[1]}
        )
        _poll_through(monkeypatch, drive)
        task = await _start(harness, project_id)

        with capture_logs() as logs:
            await task()

        row = await _row(engine, project_id)
        assert row.slide_cover is None
        assert row.hook_asset_id == photos[1]
        assert row.lock_version == 3
        assert drive.applied == [(gate, False) for gate in _GATES]
        assert _reasons(logs) == [REASON_AUTO_SELECT_MANUAL_CHOICE] * len(_GATES) + [
            REASON_AUTO_SELECT_COMPLETED
        ]


@requires_postgres
@pytest.mark.asyncio
async def test_cover_chosen_before_the_job_is_kept(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A slide_cover set when the job was scheduled is never replaced."""
    # Scenario: A cover the owner chose before the job is kept
    async with isolated_schema(_tables()) as engine:
        project_id, photos = await _running_research(engine, dirs)
        chosen = {"asset_id": photos[1], "kind": "ai_image", "staged_path": "c.webp"}
        await _set(engine, project_id, {"slide_cover": chosen})
        harness = _harness(engine, monkeypatch)
        drive = _Drive(engine=engine, project_id=project_id)
        _poll_through(monkeypatch, drive)
        task = await _start(harness, project_id)

        with capture_logs() as logs:
            await task()

        row = await _row(engine, project_id)
        assert row.slide_cover == chosen
        assert row.lock_version == 3
        assert drive.applied == [(gate, False) for gate in _GATES]
        assert _reasons(logs) == [REASON_AUTO_SELECT_OWNER_COVER] * len(_GATES) + [
            REASON_AUTO_SELECT_COMPLETED
        ]


@requires_postgres
@pytest.mark.asyncio
async def test_no_consent_writes_nothing(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With consent off the drive never stores the cover."""
    # Scenario: Without consent the drive stores nothing
    async with isolated_schema(_tables()) as engine:
        project_id, _ = await _running_research(engine, dirs)
        harness = _harness(engine, monkeypatch)
        drive = _Drive(engine=engine, project_id=project_id, consent=False)
        _poll_through(monkeypatch, drive)
        task = await _start(harness, project_id)

        with capture_logs() as logs:
            await task()

        row = await _row(engine, project_id)
        assert row.slide_cover is None
        assert row.lock_version == 3
        assert drive.applied == [(gate, False) for gate in _GATES]
        assert _reasons(logs) == [REASON_AUTO_SELECT_COMPLETED]


@requires_postgres
@pytest.mark.asyncio
async def test_failed_generation_leaves_slide_one_alone(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed run is never offered to the drive."""
    # Scenario: A failed generation leaves slide 1 alone
    async with isolated_schema(_tables()) as engine:
        project_id, photos = await _running_research(engine, dirs)
        harness = _harness(engine, monkeypatch)
        harness.editor.error = RuntimeError("grok refused")
        drive = _Drive(engine=engine, project_id=project_id)
        task = await _start(harness, project_id)

        await task()
        await drive.sleep(0.0)

        row = await _row(engine, project_id)
        assert await _result_asset(engine, project_id) is None
        assert row.slide_cover is None
        assert row.hook_asset_id == photos[0]
        assert row.lock_version == 3
        assert drive.applied == [(gate, False) for gate in _GATES]


@requires_postgres
@pytest.mark.asyncio
async def test_conflict_at_a_gate_is_tried_again_at_the_next(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A held project lock at research: the cover lands at the outline gate."""
    # Scenario: A conflict at the gate is tried again at the next gate
    async with isolated_schema(_tables()) as engine:
        project_id, _ = await _running_research(engine, dirs)
        harness = _harness(engine, monkeypatch)
        drive = _Drive(
            engine=engine, project_id=project_id, held_at=frozenset({"research"})
        )
        _poll_through(monkeypatch, drive)
        task = await _start(harness, project_id)

        await task()

        asset = await _result_asset(engine, project_id)
        row = await _row(engine, project_id)
        assert isinstance(row.slide_cover, dict)
        assert row.slide_cover["asset_id"] == asset
        assert row.lock_version == 4
        assert drive.applied[:3] == [
            ("research", False),
            ("outline", True),
            ("content", False),
        ]
