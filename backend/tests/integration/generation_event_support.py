"""A real generation-event store write a test can wait for.

``record_generation_event`` gives each write a 100 ms best-effort budget and drops
what runs over, which is right for production and wrong for an assertion: a loaded
CI runner turned a slow but healthy insert into a red test. ``SettledEventRecorder``
keeps that production path and its budget. The caller stops asserting that the
budget was met and waits for the outcome of the store write itself.
"""

from __future__ import annotations

import asyncio

from rag_backend.modules.generation_queue.domain.generation_events import (
    GenerationEventInput,
    GenerationEventRecorder,
    GenerationEventRun,
)


class SettledEventRecorder:
    """Lets each write outlive the budget, then reports how they ended."""

    def __init__(self, store: GenerationEventRecorder) -> None:
        self._store = store
        self._writes: list[asyncio.Task[bool]] = []

    async def record(
        self, run: GenerationEventRun, event: GenerationEventInput
    ) -> bool:
        """Start the store write; a budget expiry cancels only this wait."""
        write = asyncio.ensure_future(self._store.record(run, event))
        self._writes.append(write)
        return await asyncio.shield(write)

    async def settled(self) -> list[bool]:
        """Wait for every write so far and return what the store said of each."""
        return list(await asyncio.gather(*self._writes))


__all__ = ["SettledEventRecorder"]
