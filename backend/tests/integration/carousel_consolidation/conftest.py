"""Shared fixtures for carousel consolidation integration tests.

Feature: carousel_pipeline_consolidation.feature
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from tests.integration.carousel_consolidation.event_connections import EventConnections
from tests.integration.carousel_consolidation.helpers import TEST_SECRET

DATABASE_FILE = "carousel-consolidation.db"
JOURNAL_WAL = "wal"
JOURNAL_MODE_WAL = f"PRAGMA journal_mode={JOURNAL_WAL}"


@pytest.fixture(autouse=True)
def _test_settings() -> None:
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-consolidation"
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_workflow_sse_hub() -> None:
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        reset_workflow_sse_hub,
    )

    reset_workflow_sse_hub()
    yield
    reset_workflow_sse_hub()


def _record_events_on(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """Give the generation-event recorder its own connection.

    ``client`` runs the workflow on one ``StaticPool`` connection. A recorder sharing
    it would have the 100 ms budget cancel its insert on the workflow's connection,
    where the workflow's next commit can store the dropped event and later statements
    meet ``no active connection``. Production sessions each hold their own
    connection, so the recorder gets one here too, and the real budget stays in force.
    """
    from rag_backend.modules.generation_queue import bootstrap
    from rag_backend.modules.generation_queue.infrastructure.generation_events import (
        SqlGenerationEventRecorder,
    )

    event_sessions = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    def recorder(
        workflow_sessions: async_sessionmaker[AsyncSession],
    ) -> SqlGenerationEventRecorder:
        del workflow_sessions
        return SqlGenerationEventRecorder(event_sessions)

    monkeypatch.setattr(bootstrap, "SqlGenerationEventRecorder", recorder)


@pytest.fixture
async def event_connections(tmp_path: Path) -> AsyncIterator[EventConnections]:
    """Every connection the suite's event recorder opens, closed at teardown."""
    connections = EventConnections(tmp_path / DATABASE_FILE)
    yield connections
    await connections.close_all()


@pytest.fixture
async def client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    event_connections: EventConnections,
):
    """Persist the schema across recorder-driven connection invalidation.

    The file runs in WAL mode, so a reader never blocks a writer, as in Postgres.
    A budget cancel during the recorder's read leaves that cursor alive until the
    garbage collector frees it. SQLite defers closing a connection that still has
    a live statement, so in rollback-journal mode the closed connection would keep
    its read lock and the workflow's next commit would wait out the busy timeout
    and fail with ``database is locked``.
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import StaticPool

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.database.config import Base, close_db

    database_url = f"sqlite+aiosqlite:///{tmp_path / DATABASE_FILE}"
    engine = create_async_engine(database_url, echo=False, poolclass=StaticPool)
    event_engine = create_async_engine(
        database_url,
        echo=False,
        poolclass=StaticPool,
        async_creator=event_connections.open,
    )
    async with engine.connect() as conn:
        journal_mode = await conn.exec_driver_sql(JOURNAL_MODE_WAL)
        assert journal_mode.scalar_one() == JOURNAL_WAL
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _record_events_on(event_engine, monkeypatch)

    db_config.c_engine = engine
    app = create_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        ac.app = app  # type: ignore[attr-defined]
        yield ac

    db_config.c_engine = None
    await close_db()
    await engine.dispose()
    await event_engine.dispose()
