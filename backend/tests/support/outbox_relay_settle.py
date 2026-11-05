"""Finish post-commit outbox relays before a test's fixtures tear down.

``WorkflowEventService`` relays the outbox from a tracked background task, which
reads through the global engine. A test can return while that task still holds a
connection. Async tests run on a function-scoped loop and fixtures on the session
loop, so the sequence was:

1. the test body ends and its loop stops, freezing the relay mid-query;
2. the fixture disposes the engine, which swaps in a new pool;
3. the test loop closes and cancels the relay, and its connection is checked in to
   the old pool, which nothing can reach or close any more.

The garbage collector then finalizes that connection during whichever test happens
to be running, as ``ResourceWarning: ... was deleted before being closed``.

Letting the relay finish while its engine is live returns the connection to the
pool that the fixture is about to dispose. An autouse fixture cannot do this: it
tears down last, after the engine is gone. So this is a ``pytest_runtest_call``
wrapper, which runs after the test body and before any fixture teardown. The
conftests that re-export it scope it to their own tree.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest

from rag_backend.application.services import workflow_event_service


def _open_loop_relays() -> dict[asyncio.AbstractEventLoop, list[asyncio.Task[None]]]:
    """Group the unfinished relays by loop, leaving out any loop already closed."""
    by_loop: dict[asyncio.AbstractEventLoop, list[asyncio.Task[None]]] = {}
    for task in list(workflow_event_service._inflight_publishes):
        loop = task.get_loop()
        if task.done() or loop.is_closed():
            continue
        by_loop.setdefault(loop, []).append(task)
    return by_loop


async def _finish(tasks: list[asyncio.Task[None]]) -> None:
    """Wait for ``tasks``; the relay logs its own failures, so results are unused."""
    await asyncio.gather(*tasks, return_exceptions=True)


def settle_outbox_relays() -> None:
    """Run every unfinished relay to completion on the loop that owns it.

    Must be called with those loops stopped. A relay can sit on the test loop or on
    the session loop, when a fixture committed it, so one drain cannot await both.
    """
    for loop, tasks in _open_loop_relays().items():
        loop.run_until_complete(_finish(tasks))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call() -> Iterator[None]:
    """Settle the relays a test left running, even when the test failed."""
    try:
        return (yield)
    finally:
        settle_outbox_relays()
