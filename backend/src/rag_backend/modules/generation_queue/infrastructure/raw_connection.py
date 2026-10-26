"""A dedicated asyncpg connection taken from the app's SQLAlchemy engine.

PgQueuer and LISTEN need asyncpg's own connection object. Borrowing it from the
engine keeps one connection configuration (URL, credentials) for the whole
process; the connection is invalidated on exit, so its LISTEN state and session
locks never go back into the pool.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Protocol, cast

from sqlalchemy.ext.asyncio import AsyncEngine

ERR_NO_DRIVER_CONNECTION = "the engine gave no asyncpg connection"
NotifyCallback = Callable[[object, int, str, str], None]
TerminationCallback = Callable[[object], None]


class AsyncpgConnection(Protocol):
    """The part of ``asyncpg.Connection`` the queue uses."""

    async def add_listener(self, channel: str, callback: NotifyCallback) -> None:
        """Subscribe ``callback`` to NOTIFY on ``channel``."""
        ...

    async def execute(self, query: str) -> str:
        """Run one statement."""
        ...

    def is_closed(self) -> bool:
        """Whether the driver handle is already closed."""
        ...

    def terminate(self) -> None:
        """Close the driver handle and socket immediately."""
        ...

    def add_termination_listener(self, callback: TerminationCallback) -> None:
        """Call ``callback`` when the connection closes."""
        ...


@asynccontextmanager
async def asyncpg_connection(engine: AsyncEngine) -> AsyncIterator[AsyncpgConnection]:
    """A dedicated raw connection for the context; never returned to the pool."""
    connection = await engine.connect()
    driver: AsyncpgConnection | None = None
    try:
        raw = await connection.get_raw_connection()
        if raw.driver_connection is None:
            raise RuntimeError(ERR_NO_DRIVER_CONNECTION)
        driver = cast(AsyncpgConnection, raw.driver_connection)
        yield driver
    finally:
        try:
            if driver is not None:
                driver.terminate()
        finally:
            await connection.invalidate()
            await connection.close()


__all__ = [
    "AsyncpgConnection",
    "NotifyCallback",
    "TerminationCallback",
    "asyncpg_connection",
]
