"""The connections the suite's generation-event recorder opens.

Feature: carousel_generation_log_ae0556.feature
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

import aiosqlite


class EventConnections:
    """Open the recorder's connections where a cancelled write cannot orphan one.

    The budget can cancel a write while its pool reconnects. A cancelled
    ``aiosqlite`` connect still opens the database in its thread and drops it
    unclosed. Each connect here runs shielded and is kept, so teardown closes
    every connection the recorder ever opened.

    ``trace_statements`` installs an SQLite trace callback on every connection
    the recorder will open, inside that same shielded connect, so no connection
    reaches the recorder without it.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._opening: list[asyncio.Task[aiosqlite.Connection]] = []
        self._trace: Callable[[str], None] | None = None

    def trace_statements(self, callback: Callable[[str], None]) -> None:
        """Trace every statement on the connections opened from now on."""
        assert not self._opening, "trace before the recorder opens a connection"
        self._trace = callback

    def owns(self, driver_connection: object) -> bool:
        """Whether ``driver_connection`` is one the recorder opened here."""
        return any(
            opening.done()
            and not opening.cancelled()
            and opening.exception() is None
            and opening.result() is driver_connection
            for opening in self._opening
        )

    async def open(self) -> aiosqlite.Connection:
        opening = asyncio.ensure_future(self._connect())
        self._opening.append(opening)
        return await asyncio.shield(opening)

    async def _connect(self) -> aiosqlite.Connection:
        connection = await aiosqlite.connect(self._path)
        if self._trace is not None:
            await connection.set_trace_callback(self._trace)
        return connection

    async def close_all(self) -> None:
        for connection in await asyncio.gather(*self._opening):
            await connection.close()
