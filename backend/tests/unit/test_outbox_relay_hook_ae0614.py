"""This tree's conftest finishes relays before fixture teardown starts."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest

from rag_backend.application.services import workflow_event_service
from tests.support.outbox_relay_settle_wiring import (
    finished_normally,
    leave_a_relay_running,
    slow_relay,
)


@pytest.fixture
def relay_tasks() -> Iterator[list[asyncio.Task[None]]]:
    tasks: list[asyncio.Task[None]] = []
    yield tasks
    assert finished_normally(tasks) == [True]


async def test_a_relay_left_running_is_finished_before_teardown(
    relay_tasks: list[asyncio.Task[None]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(workflow_event_service, "relay_after_commit", slow_relay)

    relay_tasks.extend(leave_a_relay_running())

    assert finished_normally(relay_tasks) == [False]
