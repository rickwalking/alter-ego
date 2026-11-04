"""The autopilot's succeeded cover reaches slide 1 at the drive's gates, on Postgres.

Feature: The autopilot puts its succeeded cover on slide 1 at the next gate
(tests/features/autopilot_cover_gate_select_ae0615.feature). The autostart
helper, the generation run, the background selection, the asset store, the
locked write and the consent-gated scheduler are real; the image bridge is a
fake editor, the background task runs inline and the drive is simulated by the
poll's sleep: between two polls it passes every gate (the scheduler's
``apply_cover`` at each one, as the runner calls it) and lands in the final
review, so the poll never sees a pause, as in production. Skipped without a
Postgres ``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverPolling,
    AutoCoverSelector,
)
from rag_backend.domain.constants.cover_autoselect import (
    LOG_COVER_AUTO_SELECT,
    REASON_AUTO_SELECT_COMPLETED,
    REASON_AUTO_SELECT_MANUAL_CHOICE,
    REASON_AUTO_SELECT_OWNER_COVER,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.infrastructure.cover_autostart import (
    EditorialAutoCoverScheduler,
)
from rag_backend.modules.editorial.infrastructure import carousel_cover_autoselect
from rag_backend.modules.editorial.infrastructure.carousel_cover_autoselect import (
    EditorialAutoCoverStore,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_lock import (
    carousel_project_lock,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.test_autopilot_cover_autoselect_pg_ae0590 import (
    _harness,
    _result_asset,
    _row,
    _seed,
    _start,
)
from tests.integration.test_autopilot_cover_autostart_pg_ae0581 import _tables

_GATES = ("research", "outline", "content", "design", "images")
_NEXT = {
    "research": "outline",
    "outline": "content",
    "content": "design",
    "design": "images",
}
_FINAL_REVIEW = {
    "current_phase": "final_review",
    "phase_status": "awaiting_human",
    "status": "completed",
}


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "out"))
    get_settings.cache_clear()
    yield assets
    get_settings.cache_clear()


async def _set(engine: AsyncEngine, project_id: str, values: dict[str, object]) -> None:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            update(CarouselProjectModel)
            .where(CarouselProjectModel.id == project_id)
            .values(**values)
        )
        await session.commit()


@dataclass
class _Drive:
    """The autopilot drive between two polls: every gate, then the final review.

    ``before`` runs first (an owner write); ``at_gate`` wraps each gate's
    ``apply_cover`` (a held lock). ``applied`` records each gate's answer.
    """

    engine: AsyncEngine
    project_id: str
    consent: bool = True
    before: dict[str, object] = field(default_factory=dict)
    held_at: frozenset[str] = frozenset()
    applied: list[tuple[str, bool]] = field(default_factory=list)
    ran: bool = False

    def scheduler(self) -> EditorialAutoCoverScheduler:
        factory = async_sessionmaker(self.engine, expire_on_commit=False)
        return EditorialAutoCoverScheduler(factory, consent=self.consent)

    async def sleep(self, _seconds: float) -> None:
        if self.ran:
            return
        self.ran = True
        if self.before:
            await _set(self.engine, self.project_id, self.before)
        for gate in _GATES:
            await self.gate(gate)
        await _set(self.engine, self.project_id, _FINAL_REVIEW)

    async def gate(self, gate: str) -> None:
        """Pause at ``gate``, ask for the cover as the runner does, then resume."""
        await _set(
            self.engine,
            self.project_id,
            {"current_phase": gate, "phase_status": "awaiting_human"},
        )
        applied = await self._apply(gate)
        self.applied.append((gate, applied))
        following = _NEXT.get(gate)
        if following is not None:
            await _set(
                self.engine,
                self.project_id,
                {"current_phase": following, "phase_status": "in_progress"},
            )

    async def _apply(self, gate: str) -> bool:
        if gate not in self.held_at:
            return await self.scheduler().apply_cover(self.project_id)
        async with carousel_project_lock(self.engine, self.project_id, blocking=False):
            return await self.scheduler().apply_cover(self.project_id)


def _poll_through(monkeypatch: pytest.MonkeyPatch, drive: _Drive) -> None:
    """The background selection polls with ``drive.sleep`` between its reads."""
    factory = async_sessionmaker(drive.engine, expire_on_commit=False)

    def _selector() -> AutoCoverSelector:
        return AutoCoverSelector(
            EditorialAutoCoverStore(factory), AutoCoverPolling(sleep=drive.sleep)
        )

    monkeypatch.setattr(carousel_cover_autoselect, "auto_cover_selector", _selector)


async def _running_research(engine: AsyncEngine, dirs: Path) -> tuple[str, list[str]]:
    """The seeded carousel while research runs (the cover's scheduling time)."""
    project_id, photos = await _seed(engine, dirs)
    await _set(
        engine,
        project_id,
        {"current_phase": "research", "phase_status": "in_progress"},
    )
    return project_id, photos


def _reasons(logs: list[dict[str, object]]) -> list[object]:
    return [e.get("reason") for e in logs if e["event"] == LOG_COVER_AUTO_SELECT]


@requires_postgres
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
        assert _reasons(logs) == ["", REASON_AUTO_SELECT_COMPLETED]


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
        assert _reasons(logs) == [
            REASON_AUTO_SELECT_MANUAL_CHOICE,
            REASON_AUTO_SELECT_COMPLETED,
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
        assert _reasons(logs) == [
            REASON_AUTO_SELECT_OWNER_COVER,
            REASON_AUTO_SELECT_COMPLETED,
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
