"""Fixtures for the infrastructure unit tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from rag_backend.infrastructure.database.config import Base

_EMPTY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def sweep_engine() -> AsyncIterator[AsyncEngine]:
    """An empty database of its own for a test that counts a table-wide sweep.

    ``auto_reject_stuck`` rejects every stale row, so on the session-wide engine its
    count also holds whatever rows earlier test files left there. A row seeded just
    inside the timeout crosses it on a long enough run.
    """
    engine = create_async_engine(_EMPTY_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
