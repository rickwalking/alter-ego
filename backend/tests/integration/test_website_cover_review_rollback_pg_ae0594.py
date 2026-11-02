"""A website cover switch whose render fails or is overtaken, on Postgres.

Feature: tests/features/website_cover_review_switch_ae0594.feature. The real
stack (see ``website_cover_review_pg_support``); the render is replaced per
test. Skipped without a Postgres ``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterator
from pathlib import Path

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from rag_backend.domain.constants.cover_autoselect import LOG_COVER_AUTO_SELECT
from rag_backend.domain.constants.cover_review_switch import (
    LOG_COVER_REVIEW_ROLLBACK_FAILED,
    REASON_AUTO_SELECT_ROLLBACK_FAILED,
    REASON_AUTO_SELECT_ROLLED_BACK,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.cover_constants import (
    COVER_REVIEW_HOLD_PHASE,
    REASON_COVER_REVIEW_UNSAFE,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.editorial.infrastructure import cover_review_rollback
from rag_backend.modules.editorial.infrastructure.carousel_project_lock import (
    carousel_project_lock,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.website_cover_review_pg_support import (
    Harness,
    RunFacts,
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
    return [e.get("reason") for e in logs if e["event"] == LOG_COVER_AUTO_SELECT]


def _render_with(
    monkeypatch: pytest.MonkeyPatch, built: Harness, answer: _RenderAnswer
) -> list[str]:
    """Replace the render: record it, then run ``answer`` (errors or a side effect)."""
    calls: list[str] = []

    async def _render(_session: AsyncSession, project_id: str) -> tuple[str, ...]:
        calls.append(project_id)
        return await answer(built, project_id, len(calls))

    monkeypatch.setattr(cover_review_rollback, "_finalize", _render)
    return calls


async def _set(built: Harness, project_id: str, values: dict[str, object]) -> None:
    async with built.sessions()() as other:
        await other.execute(
            update(CarouselProjectModel)
            .where(CarouselProjectModel.id == project_id)
            .values(**values)
        )
        await other.commit()


async def _assert_restored(built: Harness, project_id: str, photo: str) -> None:
    model = await row(built, project_id)
    assert model.slide_cover is None
    assert model.hook_asset_id == photo
    assert model.needs_republish_since is None


@requires_postgres
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [("render_failed",), RuntimeError("boom"), KeyError("x")]
)
async def test_a_failed_render_of_any_kind_rolls_the_cover_back(
    dirs: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: tuple[str, ...] | Exception,
) -> None:
    """Any render failure: slide 1 back, rendered again, the review re-sent."""
    # Scenario: A failed or overtaken website cover switch is rolled back
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        await seed_run(built, project_id, _AWAITING)

        async def _fails_once(_b: Harness, _p: str, n: int) -> tuple[str, ...]:
            if n > 1:
                return ()
            if isinstance(failure, Exception):
                raise failure
            return failure

        calls = _render_with(monkeypatch, built, _fails_once)
        with capture_logs() as logs:
            await (await website_task(built, project_id, photos[0]))()

        await _assert_restored(built, project_id, photos[0])
        assert (await row(built, project_id)).lock_version == 5
        assert len(calls) == 2
        assert _skips(logs) == [REASON_AUTO_SELECT_ROLLED_BACK]
        facts = await run_facts(built, project_id)
        assert facts is not None
        assert facts.state == AutopilotRunState.REWORKING.value
        assert facts.rework_phase is None


@requires_postgres
@pytest.mark.asyncio
async def test_an_approval_before_the_render_is_never_rendered_onto(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Approved between the write and the render: no forward render; a failing
    re-render of the restored cover is ``rollback_failed`` and the marker stays."""
    # Scenario: A failed or overtaken website cover switch is rolled back
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        await seed_run(built, project_id, _AWAITING)
        original = cover_review_rollback.still_in_review

        async def _approved_first(session: AsyncSession, pid: str) -> bool:
            await _set(built, pid, {"workflow_status": "approved_for_publish"})
            return await original(session, pid)

        async def _rerender_fails(_b: Harness, _p: str, _n: int) -> tuple[str, ...]:
            return ("build_in_progress",)

        monkeypatch.setattr(cover_review_rollback, "still_in_review", _approved_first)
        calls = _render_with(monkeypatch, built, _rerender_fails)
        with capture_logs() as logs:
            await (await website_task(built, project_id, photos[0]))()

        model = await row(built, project_id)
        assert model.slide_cover is None
        assert model.needs_republish_since is not None
        assert len(calls) == 1
        assert _skips(logs) == [REASON_AUTO_SELECT_ROLLBACK_FAILED]
        facts = await run_facts(built, project_id)
        assert facts is not None
        assert facts.state == AutopilotRunState.ESCALATED.value


@requires_postgres
@pytest.mark.asyncio
async def test_an_owner_pick_of_the_same_asset_meanwhile_is_kept(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rollback compares the whole cover, so the owner's own value survives."""
    # Scenario: A failed or overtaken website cover switch is rolled back
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)

        async def _owner_repicks(b: Harness, p: str, _n: int) -> tuple[str, ...]:
            asset = await result_asset(b, p)
            await _set(
                b,
                p,
                {
                    "slide_cover": {
                        "asset_id": asset,
                        "kind": "ai_image",
                        "staged_path": "o.webp",
                        "credit": "",
                    }
                },
            )
            return ("render_failed",)

        calls = _render_with(monkeypatch, built, _owner_repicks)
        await (await website_task(built, project_id, photos[0]))()

        model = await row(built, project_id)
        assert isinstance(model.slide_cover, dict)
        assert model.slide_cover["staged_path"] == "o.webp"
        assert len(calls) == 1


@requires_postgres
@pytest.mark.asyncio
async def test_a_restore_that_never_gets_the_lock_escalates_the_run(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Another holder keeps the project lock: rollback_failed, the run escalated."""
    # Scenario: A failed or overtaken website cover switch is rolled back
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        await seed_run(built, project_id, _AWAITING)
        monkeypatch.setattr(cover_review_rollback, "ROLLBACK_LOCK_ATTEMPTS", 2)
        monkeypatch.setattr(cover_review_rollback, "ROLLBACK_LOCK_RETRY_SECONDS", 0.0)
        done = asyncio.Event()
        holders: list[asyncio.Task[None]] = []
        original = cover_review_rollback._restore

        async def _locked_restore(
            session: AsyncSession, rollback: cover_review_rollback.CoverRollback
        ) -> str:
            if not holders:
                locked = asyncio.Event()

                async def _hold() -> None:
                    async with carousel_project_lock(
                        built.engine, project_id, blocking=False
                    ):
                        locked.set()
                        await done.wait()

                holders.append(asyncio.get_running_loop().create_task(_hold()))
                await locked.wait()
            return await original(session, rollback)

        async def _fails(_b: Harness, _p: str, _n: int) -> tuple[str, ...]:
            return ("build_in_progress",)

        monkeypatch.setattr(cover_review_rollback, "_restore", _locked_restore)
        _render_with(monkeypatch, built, _fails)
        with capture_logs() as logs:
            await (await website_task(built, project_id, photos[0]))()
        done.set()
        await asyncio.gather(*holders)

        model = await row(built, project_id)
        assert isinstance(model.slide_cover, dict)
        assert model.needs_republish_since is not None
        assert _skips(logs) == [REASON_AUTO_SELECT_ROLLBACK_FAILED]
        assert [e for e in logs if e["event"] == LOG_COVER_REVIEW_ROLLBACK_FAILED]
        facts = await run_facts(built, project_id)
        assert facts == RunFacts(
            state=AutopilotRunState.ESCALATED.value,
            reason=REASON_COVER_REVIEW_UNSAFE,
            rework_phase=None,
        )


@requires_postgres
@pytest.mark.asyncio
async def test_a_process_dying_mid_switch_leaves_the_review_held_and_unmarked(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recoverable: the marker keeps approval refused for the sweep; the run held."""
    # Scenario: A Telegram review hold that outlives its task is escalated
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, photos = await seed(built, dirs)
        await seed_run(built, project_id, _AWAITING)

        async def _killed(_b: Harness, _p: str, _n: int) -> tuple[str, ...]:
            raise asyncio.CancelledError

        _render_with(monkeypatch, built, _killed)
        with pytest.raises(asyncio.CancelledError):
            await (await website_task(built, project_id, photos[0]))()

        model = await row(built, project_id)
        assert isinstance(model.slide_cover, dict)
        assert model.needs_republish_since is not None
        facts = await run_facts(built, project_id)
        assert facts is not None
        assert facts.state == AutopilotRunState.REWORKING.value
        assert facts.rework_phase == COVER_REVIEW_HOLD_PHASE
