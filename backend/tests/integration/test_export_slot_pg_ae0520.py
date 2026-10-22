"""The export slot waits on the Postgres advisory lock held by another process.

Feature: backend/tests/features/carousel_generation_load_ae0520.feature
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from rag_backend.infrastructure.external import export_lock
from tests.integration.pg_schema_support import PG_URL, requires_postgres

_HOLDERS_SQL = text(
    "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND granted"
    " AND objid = :objid"
)
_OBJID = export_lock.EXPORT_LOCK_KEY & 0xFFFFFFFF
_STILL_WAITING_SECONDS = 0.3


@requires_postgres
async def test_slot_waits_for_another_session_holding_the_lock() -> None:
    # Scenario: Exports in different processes wait on the Postgres advisory lock
    other_process = create_async_engine(PG_URL)
    app_engine = create_async_engine(PG_URL)
    entered = asyncio.Event()

    async def export() -> None:
        async with export_lock.export_slot():
            entered.set()

    try:
        async with other_process.connect() as holder:
            await holder.execute(
                text("SELECT pg_advisory_lock(:key)"),
                {"key": export_lock.EXPORT_LOCK_KEY},
            )
            with patch.object(export_lock.database_config, "c_engine", app_engine):
                task = asyncio.create_task(export())
                await asyncio.sleep(_STILL_WAITING_SECONDS)
                assert not entered.is_set()
                await holder.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": export_lock.EXPORT_LOCK_KEY},
                )
                await asyncio.wait_for(task, timeout=5)
        assert entered.is_set()
        async with app_engine.connect() as conn:
            holders = await conn.scalar(_HOLDERS_SQL, {"objid": _OBJID})
        assert holders == 0
    finally:
        await app_engine.dispose()
        await other_process.dispose()


async def _holders(engine: AsyncEngine) -> int:
    async with engine.connect() as conn:
        return int(await conn.scalar(_HOLDERS_SQL, {"objid": _OBJID}) or 0)


@requires_postgres
async def test_cancelled_export_releases_the_lock() -> None:
    # Scenario: An export that fails or is cancelled releases the Postgres lock
    app_engine = create_async_engine(PG_URL)
    observer = create_async_engine(PG_URL)
    entered = asyncio.Event()

    async def hold_forever() -> None:
        async with export_lock.export_slot():
            entered.set()
            await asyncio.Event().wait()

    try:
        with patch.object(export_lock.database_config, "c_engine", app_engine):
            task = asyncio.create_task(hold_forever())
            await asyncio.wait_for(entered.wait(), timeout=5)
            assert await _holders(observer) == 1
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert await _holders(observer) == 0
            async with asyncio.timeout(5), export_lock.export_slot():
                assert await _holders(observer) == 1
        assert await _holders(observer) == 0
    finally:
        await app_engine.dispose()
        await observer.dispose()


@requires_postgres
async def test_failed_export_releases_the_lock() -> None:
    # Scenario: An export that fails or is cancelled releases the Postgres lock
    app_engine = create_async_engine(PG_URL)
    observer = create_async_engine(PG_URL)
    try:
        with patch.object(export_lock.database_config, "c_engine", app_engine):
            with pytest.raises(RuntimeError):
                async with export_lock.export_slot():
                    raise RuntimeError("chromium crashed")
            assert await _holders(observer) == 0
            async with asyncio.timeout(5), export_lock.export_slot():
                assert await _holders(observer) == 1
    finally:
        await app_engine.dispose()
        await observer.dispose()


@requires_postgres
async def test_failed_unlock_never_leaves_the_lock_on_a_pooled_connection() -> None:
    # Scenario: An export that fails or is cancelled releases the Postgres lock
    app_engine = create_async_engine(PG_URL, pool_size=1, max_overflow=0)
    observer = create_async_engine(PG_URL)
    broken_unlock = text("SELECT pg_advisory_unlock_missing(:key)")
    try:
        with (
            patch.object(export_lock.database_config, "c_engine", app_engine),
            patch.object(export_lock, "_UNLOCK_SQL", broken_unlock),
        ):
            with pytest.raises(DBAPIError):
                async with export_lock.export_slot():
                    assert await _holders(observer) == 1
            assert await _holders(observer) == 0
    finally:
        await app_engine.dispose()
        await observer.dispose()
