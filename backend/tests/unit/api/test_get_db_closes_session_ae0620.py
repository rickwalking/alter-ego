"""A request's database session closes with the request, however the request ends.

Feature: tests/features/request_session_closed_with_the_request_ae0620.feature
"""

from __future__ import annotations

import asyncio
import gc
import warnings
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import QueuePool

import rag_backend.infrastructure.database.config as db_config
from rag_backend.api.dependencies.database import get_db

_BASE_URL = "http://test"
_DATABASE_FILE = "session.db"
_DRIVER_URL = "sqlite+aiosqlite:///"
_LEAK_MARK = "was deleted before being closed"
_OK_PATH = "/ok"
_REFUSED_PATH = "/refused"
_CRASH_PATH = "/crash"
_READ_ONE = text("SELECT 1")
_CRASH_MESSAGE = "unexpected failure"

_Session = Annotated[AsyncSession, Depends(get_db)]


class _HandlerFailedError(Exception):
    """The failure a handler raises in these tests."""


def _app() -> FastAPI:
    app = FastAPI()

    @app.get(_OK_PATH)
    async def succeed(db: _Session) -> dict[str, int]:
        return {"value": (await db.execute(_READ_ONE)).scalar_one()}

    @app.get(_REFUSED_PATH)
    async def refuse(db: _Session) -> None:
        await db.execute(_READ_ONE)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    @app.get(_CRASH_PATH)
    async def crash(db: _Session) -> None:
        await db.execute(_READ_ONE)
        raise _HandlerFailedError(_CRASH_MESSAGE)

    return app


def _client() -> AsyncClient:
    transport = ASGITransport(app=_app(), raise_app_exceptions=False)
    return AsyncClient(transport=transport, base_url=_BASE_URL)


def _checked_out(engine: AsyncEngine) -> int:
    pool = engine.sync_engine.pool
    assert isinstance(pool, QueuePool)
    return pool.checkedout()


@pytest.fixture
async def engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncEngine]:
    """A file database, whose pool keeps connections apart as Postgres does."""
    created = create_async_engine(f"{_DRIVER_URL}{tmp_path / _DATABASE_FILE}")
    monkeypatch.setattr(db_config, "c_engine", created)
    yield created
    await created.dispose()


# Scenario: A handler that succeeds releases its connection
async def test_a_successful_request_releases_its_connection(
    engine: AsyncEngine,
) -> None:
    async with _client() as client:
        response = await client.get(_OK_PATH)

    assert response.status_code == status.HTTP_200_OK
    assert _checked_out(engine) == 0


# Scenario: A handler that refuses the request releases its connection
async def test_a_refused_request_releases_its_connection(engine: AsyncEngine) -> None:
    async with _client() as client:
        response = await client.get(_REFUSED_PATH)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert _checked_out(engine) == 0


# Scenario: A handler that crashes releases its connection
async def test_a_crashed_request_releases_its_connection(engine: AsyncEngine) -> None:
    async with _client() as client:
        response = await client.get(_CRASH_PATH)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert _checked_out(engine) == 0


# Scenario: The session is closed when the dependency is thrown into
async def test_throwing_into_the_dependency_releases_the_connection(
    engine: AsyncEngine,
) -> None:
    dependency = get_db()
    session = await anext(dependency)
    await session.execute(_READ_ONE)
    assert _checked_out(engine) == 1

    with pytest.raises(_HandlerFailedError):
        await dependency.athrow(_HandlerFailedError(_CRASH_MESSAGE))

    assert _checked_out(engine) == 0


async def _refuse_then_dispose(path: Path) -> None:
    engine = create_async_engine(f"{_DRIVER_URL}{path}")
    previous = db_config.c_engine
    db_config.c_engine = engine
    try:
        async with _client() as client:
            await client.get(_REFUSED_PATH)
    finally:
        db_config.c_engine = previous
        await engine.dispose()


# Scenario: A refused request leaves nothing for the garbage collector
def test_a_refused_request_leaves_no_unclosed_connection(tmp_path: Path) -> None:
    """Own loop: the old code only dropped the connection when that loop shut down."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        asyncio.run(_refuse_then_dispose(tmp_path / _DATABASE_FILE))
        gc.collect()

    assert [str(w.message) for w in caught if _LEAK_MARK in str(w.message)] == []
