"""The non-blocking session advisory lock around one full maintenance pass."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.modules.generation_queue.constants import MAINTENANCE_ADVISORY_KEY

_POSTGRESQL = "postgresql"
_AUTOCOMMIT = "AUTOCOMMIT"
_KEY = "key"
_TRY_LOCK = text("SELECT pg_try_advisory_lock(:key)")


class PostgresMaintenanceLock:
    """Hold the full-pass lock on a dedicated connection, never waiting."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def hold(self) -> AsyncIterator[bool]:
        """Yield false immediately when another session owns the full pass."""
        if self._engine.dialect.name != _POSTGRESQL:
            yield True
            return
        connection = await self._engine.connect()
        try:
            await connection.execution_options(isolation_level=_AUTOCOMMIT)
            acquired = await connection.scalar(
                _TRY_LOCK, {_KEY: MAINTENANCE_ADVISORY_KEY}
            )
            yield bool(acquired)
        finally:
            await connection.invalidate()
            await connection.close()


__all__ = ["PostgresMaintenanceLock"]
