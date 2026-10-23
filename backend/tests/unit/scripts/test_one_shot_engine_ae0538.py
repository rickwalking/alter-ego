"""The guarded one-shots run on a dedicated engine that is always disposed of."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from rag_backend.scripts import carousel_archived_at, cli_support


def _fake_engine(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    engine = MagicMock(spec=AsyncEngine)
    engine.dispose = AsyncMock()
    monkeypatch.setattr(cli_support, "create_async_engine", lambda *_a, **_k: engine)
    return engine


async def test_the_runner_result_is_returned_and_the_engine_disposed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The dedicated engine is handed to the runner and disposed afterwards."""
    engine = _fake_engine(monkeypatch)
    seen: list[AsyncEngine] = []

    async def run(given: AsyncEngine) -> int:
        seen.append(given)
        return 3

    assert await cli_support.run_on_own_engine(run) == 3
    assert seen == [engine]
    engine.dispose.assert_awaited_once()


async def test_the_engine_is_disposed_when_the_runner_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failing runner still releases the engine."""
    engine = _fake_engine(monkeypatch)

    async def run(_given: AsyncEngine) -> int:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await cli_support.run_on_own_engine(run)
    engine.dispose.assert_awaited_once()


def test_the_archived_at_command_runs_end_to_end_on_its_own_engine(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--apply --verify`` runs through the shared runner (SQLite: a no-op, exit 0).

    ``main`` starts its own event loop, so it runs in a worker thread, away from
    the test session's loop.
    """
    monkeypatch.setattr(
        cli_support,
        "create_async_engine",
        lambda *_a, **_k: create_async_engine("sqlite+aiosqlite:///:memory:"),
    )

    with ThreadPoolExecutor(max_workers=1) as pool:
        code = pool.submit(carousel_archived_at.main, ["--apply", "--verify"]).result()

    assert code == carousel_archived_at.EXIT_OK
    assert (
        "carousel archived_at: not Postgres, nothing to do" in capsys.readouterr().out
    )
