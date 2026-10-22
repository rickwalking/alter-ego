"""The export slot waits on the Postgres advisory lock held by another process.

Feature: backend/tests/features/carousel_generation_load_ae0520.feature
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

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
