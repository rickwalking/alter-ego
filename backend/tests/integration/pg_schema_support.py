"""A throwaway Postgres schema for concurrency tests.

The shared test database is also migrated by the Alembic gates, so these
tests never create tables in ``public``. Each test gets its own schema,
creates only the tables it needs there, and drops the schema afterwards.
Skipped unless ``DATABASE_URL`` points at Postgres.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from rag_backend.infrastructure.database.config import Base

PG_URL = os.environ.get("DATABASE_URL", "")
requires_postgres = pytest.mark.skipif(
    "postgresql" not in PG_URL,
    reason="concurrency tests need a Postgres DATABASE_URL",
)
_SCHEMA_PREFIX = "qa_r2_"


@asynccontextmanager
async def isolated_schema(names: Sequence[str]) -> AsyncIterator[AsyncEngine]:
    """An engine whose ``search_path`` is a fresh schema holding these tables."""
    tables = [Base.metadata.tables[name] for name in names]
    schema = f"{_SCHEMA_PREFIX}{uuid4().hex[:12]}"
    admin = create_async_engine(PG_URL)
    async with admin.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        PG_URL, connect_args={"server_settings": {"search_path": schema}}
    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, tables=tables)
        yield engine
    finally:
        await engine.dispose()
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()
