"""One carousel export at a time, across tasks and processes.

Every ``export_slides`` call launches a headless Chromium (HD at 2x scale), the
heaviest local step of a carousel run. ``export_slot`` admits one export at a
time: an asyncio lock for the tasks of this process, then a session-scoped
Postgres advisory lock held on a dedicated connection for every other process.
The connection is checked out for the whole export and the lock released in a
``finally``; a dropped connection releases it server-side. Without a Postgres
engine (SQLite tests, scripts that never call ``init_db``) only the process lock
applies.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from weakref import WeakKeyDictionary

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database import config as database_config
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

EXPORT_LOCK_KEY = 0x41455850
LOG_EXPORT_SLOT_ACQUIRED = "carousel_export_slot_acquired"

_POSTGRESQL_DIALECT = "postgresql"
_KEY_PARAM = "key"
_LOCK_SQL = text("SELECT pg_advisory_lock(:key)")
_UNLOCK_SQL = text("SELECT pg_advisory_unlock(:key)")
_MS_PER_SECOND = 1000

_PROCESS_LOCKS: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock] = (
    WeakKeyDictionary()
)


def _process_lock() -> asyncio.Lock:
    """The lock of the running event loop (one per loop, created on first use)."""
    loop = asyncio.get_running_loop()
    lock = _PROCESS_LOCKS.get(loop)
    if lock is None:
        lock = asyncio.Lock()
        _PROCESS_LOCKS[loop] = lock
    return lock


def _postgres_engine() -> AsyncEngine | None:
    """The app engine when it is initialized and Postgres, else None."""
    engine = database_config.c_engine
    if engine is None or engine.dialect.name != _POSTGRESQL_DIALECT:
        return None
    return engine


@asynccontextmanager
async def _advisory_slot(engine: AsyncEngine) -> AsyncIterator[None]:
    """Hold the export advisory lock on a dedicated connection."""
    connection = await engine.connect()
    try:
        await connection.execute(_LOCK_SQL, {_KEY_PARAM: EXPORT_LOCK_KEY})
        try:
            yield
        finally:
            await connection.execute(_UNLOCK_SQL, {_KEY_PARAM: EXPORT_LOCK_KEY})
    finally:
        await connection.close()


@asynccontextmanager
async def export_slot() -> AsyncIterator[None]:
    """Wait for the single export slot, hold it for the context, log the wait."""
    started = time.monotonic()
    async with _process_lock():
        engine = _postgres_engine()
        if engine is None:
            _log_acquired(started, cross_process=False)
            yield
            return
        async with _advisory_slot(engine):
            _log_acquired(started, cross_process=True)
            yield


def _log_acquired(started: float, *, cross_process: bool) -> None:
    waited_ms = round((time.monotonic() - started) * _MS_PER_SECOND)
    logger.info(
        LOG_EXPORT_SLOT_ACQUIRED,
        waited_ms=waited_ms,
        cross_process=cross_process,
    )


__all__ = ["EXPORT_LOCK_KEY", "LOG_EXPORT_SLOT_ACQUIRED", "export_slot"]
