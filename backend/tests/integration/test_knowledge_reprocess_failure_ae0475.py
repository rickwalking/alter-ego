"""Reprocess failures are committed through the real route and Unit of Work.

Feature: knowledge_ingestion_failure_ae0475.feature
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.models import Document, DocumentStatus, UserRole
from tests.integration.conftest import (
    TEST_SECRET,
    auth_headers_for,
    create_test_user,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

    from rag_backend.domain.models import User
    from rag_backend.infrastructure.container import Container

_REASON = "embedding service unavailable"


@dataclass
class _Env:
    app: FastAPI
    owner: User
    container: Container


@pytest_asyncio.fixture
async def env() -> AsyncGenerator[_Env, None]:
    """App over in-memory SQLite with a failing processor and a stub vector store."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.container import get_container
    from rag_backend.infrastructure.database.config import Base, close_db

    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-integration-tests"
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    owner = await create_test_user("kb-ae0475@integration.test", UserRole.EDITOR)
    app = create_app()
    container = get_container()
    store = AsyncMock()
    container.vector_store.override(store)
    processor = MagicMock()
    processor.process = AsyncMock(side_effect=RuntimeError(_REASON))
    processor.estimate_chunks = MagicMock(return_value=1)
    container.document_processor.override(processor)
    try:
        yield _Env(app=app, owner=owner, container=container)
    finally:
        container.vector_store.reset_override()
        container.document_processor.reset_override()
        db_config.c_engine = None
        await close_db()
        await engine.dispose()


async def _seed(container: Container, owner_id: UUID) -> Document:
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        repo = container.document_repository(session=session)
        created = await repo.create(
            Document(title="my_resume.pdf", content="Resume text.", owner_id=owner_id)
        )
        await session.commit()
        return created


@pytest.mark.asyncio
async def test_failed_reprocess_is_saved_with_the_reason(env: _Env) -> None:
    # Scenario: A failed reprocess is saved as failed with the reason
    document = await _seed(env.container, env.owner.id)
    transport = ASGITransport(app=env.app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=auth_headers_for(env.owner),
    ) as client:
        response = await client.post(f"/api/documents/{document.id}/reprocess")
        again = await client.get(f"/api/documents/{document.id}")

    assert response.status_code == 200
    assert response.json()["status"] == DocumentStatus.FAILED.value
    assert response.json()["error_message"] == f"RuntimeError: {_REASON}"
    assert again.json()["status"] == DocumentStatus.FAILED.value
    assert again.json()["error_message"] == f"RuntimeError: {_REASON}"
