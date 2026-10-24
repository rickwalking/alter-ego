"""The per-project drive lock: the only ownership primitive of the queue.

Session advisory locks (``pg_try_advisory_lock``) held on one dedicated AUTOCOMMIT
connection for the whole drive, never returned to the pool mid-phase. Its keys
live in their own space (``drive:`` digest), apart from the artifact-mutation
lock: a drive runs the autopilot's own autofix steps, which take the mutation
lock from another session, and advisory locks are not re-entrant across sessions.

A busy key is retried for up to 60 s, then ``DriveLockBusyError`` (the job comes back
in 2 min). While the drive runs, a watchdog pings the lock connection every 30 s;
when the ping fails the drive is cancelled with ``DriveLockLostError``: the server has
dropped the lock, so another worker may already own the project. The connection
is closed (not pooled) on every exit, which releases whatever it still holds.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from rag_backend.modules.generation_queue.constants import (
    LOCK_POLL_SECONDS,
    LOCK_WAIT_SECONDS,
    LOCK_WATCH_SECONDS,
    LOG_LOCK_LOST,
)
from rag_backend.modules.generation_queue.domain.errors import (
    DriveLockBusyError,
    DriveLockLostError,
)

logger = structlog.get_logger()

_KEY_PREFIX = "drive:"
_DIGEST_BYTES = 8
_AUTOCOMMIT = "AUTOCOMMIT"
_POSTGRESQL = "postgresql"
_TRY_LOCK_SQL = text("SELECT pg_try_advisory_lock(:key)")
_PING_SQL = text("SELECT 1")
_KEY = "key"


def drive_lock_key(name: str) -> int:
    """Stable signed 64-bit key for a drive-lock name."""
    digest = hashlib.sha256(f"{_KEY_PREFIX}{name}".encode()).digest()
    return int.from_bytes(digest[:_DIGEST_BYTES], "big", signed=True)


@dataclass(frozen=True)
class DriveLockTiming:
    """How long to wait for a busy key and how often to check the connection."""

    wait_seconds: float = LOCK_WAIT_SECONDS
    poll_seconds: float = LOCK_POLL_SECONDS
    watch_seconds: float = LOCK_WATCH_SECONDS


class PostgresDriveLock:
    """Implements ``DriveLock`` with session advisory locks."""

    def __init__(
        self, engine: AsyncEngine, timing: DriveLockTiming | None = None
    ) -> None:
        self._engine = engine
        self._timing = timing or DriveLockTiming()

    @asynccontextmanager
    async def hold(self, keys: Sequence[str]) -> AsyncIterator[None]:
        """Hold every key (sorted, so two drivers never deadlock) for the context."""
        if self._engine.dialect.name != _POSTGRESQL:
            yield
            return
        connection = await self._engine.connect()
        try:
            await connection.execution_options(isolation_level=_AUTOCOMMIT)
            for name in sorted(set(keys)):
                await self._acquire(connection, drive_lock_key(name))
            async with _watched(connection, self._timing.watch_seconds):
                yield
        finally:
            await connection.invalidate()
            await connection.close()

    async def _acquire(self, connection: AsyncConnection, key: int) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timing.wait_seconds
        while not await connection.scalar(_TRY_LOCK_SQL, {_KEY: key}):
            if loop.time() >= deadline:
                raise DriveLockBusyError
            await asyncio.sleep(self._timing.poll_seconds)


@dataclass(frozen=True)
class _Watch:
    """The lock connection, the ping period and the drive to cancel."""

    connection: AsyncConnection
    every: float
    lost: asyncio.Event
    driver: asyncio.Task[object] | None


@asynccontextmanager
async def _watched(connection: AsyncConnection, every: float) -> AsyncIterator[None]:
    """Cancel the drive with ``DriveLockLostError`` when the lock connection dies."""
    watch = _Watch(connection, every, asyncio.Event(), asyncio.current_task())
    watchdog = asyncio.create_task(_watch(watch))
    try:
        yield
    except asyncio.CancelledError:
        if watch.lost.is_set() and watch.driver is not None:
            watch.driver.uncancel()
            raise DriveLockLostError from None
        raise
    finally:
        watchdog.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watchdog


async def _watch(watch: _Watch) -> None:
    while True:
        await asyncio.sleep(watch.every)
        try:
            await watch.connection.execute(_PING_SQL)
        except Exception:
            logger.error(LOG_LOCK_LOST, exc_info=True)
            watch.lost.set()
            if watch.driver is not None:
                watch.driver.cancel()
            return


__all__ = ["DriveLockTiming", "PostgresDriveLock", "drive_lock_key"]
