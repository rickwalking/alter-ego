"""Shared check that a conftest wires the relay settle hook."""

from __future__ import annotations

import asyncio

from rag_backend.application.services import workflow_event_service

_RELAY_SECONDS = 0.01


async def slow_relay(publisher: object) -> None:
    """Stand in for a relay still reading when the test body returns."""
    await asyncio.sleep(_RELAY_SECONDS)


def leave_a_relay_running() -> list[asyncio.Task[None]]:
    """Queue a relay the way a commit does and return it unfinished."""
    workflow_event_service._schedule_relay([object()])
    return list(workflow_event_service._inflight_publishes)


def finished_normally(tasks: list[asyncio.Task[None]]) -> list[bool]:
    """Report, per relay, that it ran to its end instead of being cancelled."""
    return [task.done() and not task.cancelled() for task in tasks]
