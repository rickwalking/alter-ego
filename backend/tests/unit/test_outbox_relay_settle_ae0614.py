"""A relay frozen past its engine's dispose leaks an aiosqlite connection.

The first test is the seeded violation: it runs the real relay and engine through
the lifecycle that failed in CI and shows the warning fires. The others show that
settling the relay first closes the connection, and that the hook does so in a test.
"""

from __future__ import annotations

import asyncio
import gc
import warnings
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from rag_backend.application.services import workflow_event_service
from rag_backend.infrastructure.database import config as db_config
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from tests.support.outbox_relay_settle import settle_outbox_relays

_PUBLISH_SECONDS = 0.01
_AIOSQLITE_MARK = "aiosqlite"
_OUTBOX_ROW = {
    "event_id": "ae0614-event",
    "event_type": "ae0614.seeded",
    "aggregate_id": "ae0614-aggregate",
    "aggregate_type": "ae0614",
    "version": 1,
    "payload": {},
    "metadata_json": {},
    "event_timestamp": "2026-11-04T00:00:00+00:00",
    "attempts": 0,
}


class _SlowPublisher:
    """Holds the relay inside its session long enough for the test body to end."""

    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def publish(self, stream: str, event: dict[str, object]) -> None:
        self.started.set()
        await asyncio.sleep(_PUBLISH_SECONDS)


async def _seed_outbox(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(EventOutboxModel.__table__.create)
        await conn.execute(insert(EventOutboxModel).values(**_OUTBOX_ROW))
    await engine.dispose()


async def _test_body(publisher: _SlowPublisher) -> None:
    """Return as a request handler would: right after the commit queued the relay."""
    workflow_event_service._schedule_relay([publisher])
    await publisher.started.wait()


def _close_like_pytest_asyncio(loop: asyncio.AbstractEventLoop) -> None:
    tasks = asyncio.all_tasks(loop)
    for task in tasks:
        task.cancel()
    if tasks:
        loop.run_until_complete(asyncio.wait(tasks))
    loop.close()


def _run_lifecycle(engine: AsyncEngine, before_dispose: Callable[[], None]) -> None:
    """Run the suite's loop order: test body, fixture dispose, test loop close."""
    session_loop = asyncio.new_event_loop()
    test_loop = asyncio.new_event_loop()
    try:
        session_loop.run_until_complete(_seed_outbox(engine))
        test_loop.run_until_complete(_test_body(_SlowPublisher()))
        before_dispose()
        session_loop.run_until_complete(engine.dispose())
    finally:
        _close_like_pytest_asyncio(test_loop)
        session_loop.close()


def _unclosed_connection_warnings(lifecycle: Callable[[], None]) -> list[str]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        lifecycle()
        gc.collect()
    messages = [
        str(item.message) for item in caught if item.category is ResourceWarning
    ]
    return [message for message in messages if _AIOSQLITE_MARK in message]


@pytest.fixture
def sqlite_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[AsyncEngine]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'relay.db'}")
    monkeypatch.setattr(db_config, "c_engine", engine)
    yield engine


def test_a_relay_frozen_past_dispose_leaks_its_connection(
    sqlite_engine: AsyncEngine,
) -> None:
    def do_nothing() -> None:
        return None

    leaks = _unclosed_connection_warnings(
        lambda: _run_lifecycle(sqlite_engine, do_nothing)
    )

    assert len(leaks) == 1
    assert "was deleted before being closed" in leaks[0]


def test_a_settled_relay_leaves_no_connection_behind(
    sqlite_engine: AsyncEngine,
) -> None:
    leaks = _unclosed_connection_warnings(
        lambda: _run_lifecycle(sqlite_engine, settle_outbox_relays)
    )

    assert leaks == []


def test_settling_with_no_relay_is_a_no_op() -> None:
    assert workflow_event_service._inflight_publishes == set()

    settle_outbox_relays()

    assert workflow_event_service._inflight_publishes == set()


def test_a_relay_on_a_closed_loop_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loop = asyncio.new_event_loop()
    stranded = loop.create_task(asyncio.sleep(0))
    loop.close()
    monkeypatch.setattr(workflow_event_service, "_inflight_publishes", {stranded})

    settle_outbox_relays()

    assert not stranded.done()
    stranded.get_coro().close()
    stranded._log_destroy_pending = False


def test_relays_on_two_loops_are_each_settled_on_their_own_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def relay() -> None:
        await asyncio.sleep(0)

    loops = [asyncio.new_event_loop(), asyncio.new_event_loop()]
    tasks = {loop.create_task(relay()) for loop in loops}
    monkeypatch.setattr(workflow_event_service, "_inflight_publishes", tasks)

    settle_outbox_relays()

    for loop in loops:
        loop.close()
    assert all(task.done() and not task.cancelled() for task in tasks)
