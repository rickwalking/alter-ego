"""ASGI harness for owner/admin manual recovery endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import rag_backend.infrastructure.database.config as db_config
from rag_backend.api.app import create_app
from rag_backend.domain.models import User, UserRole
from tests.integration.conftest import auth_headers_for, create_test_user
from tests.integration.manual_reprocess_support import RecordingNotifier
from tests.integration.queue_flow_db_support import queue_flow_engine


@dataclass
class RecoveryApiHarness:
    """A real app, its disposable database and three authenticated actors."""

    app: FastAPI
    client: AsyncClient
    sessions: async_sessionmaker[AsyncSession]
    owner: User
    admin: User
    reviewer: User
    notifier: RecordingNotifier

    def headers(self, actor: User) -> dict[str, str]:
        """JWT headers for one actor."""
        return auth_headers_for(actor)


@asynccontextmanager
async def recovery_api_harness(
    tmp_path: Path,
) -> AsyncIterator[RecoveryApiHarness]:
    """Run the registered routes on a disposable queue-flow database."""
    async with queue_flow_engine(tmp_path) as engine:
        previous = db_config.c_engine
        db_config.c_engine = engine
        try:
            owner = await create_test_user("owner@reprocess.test", UserRole.EDITOR)
            admin = await create_test_user("admin@reprocess.test", UserRole.ADMIN)
            reviewer = await create_test_user(
                "reviewer@reprocess.test", UserRole.EDITOR
            )
            app = create_app()
            notifier = RecordingNotifier()
            app.state.manual_recovery_notifier = notifier
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                yield RecoveryApiHarness(
                    app=app,
                    client=client,
                    sessions=sessions,
                    owner=owner,
                    admin=admin,
                    reviewer=reviewer,
                    notifier=notifier,
                )
        finally:
            db_config.c_engine = previous


__all__ = ["RecoveryApiHarness", "recovery_api_harness"]
