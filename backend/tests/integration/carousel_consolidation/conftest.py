"""Shared fixtures for carousel consolidation integration tests.

Feature: carousel_pipeline_consolidation.feature
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

from tests.integration.carousel_consolidation.helpers import TEST_SECRET

pytest_plugins: list[str] = []


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


@pytest.fixture
async def client():
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
