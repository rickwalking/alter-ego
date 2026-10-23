"""Shared app, users and callers for the conversation access tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.models import User, UserRole
from tests.integration.conftest import auth_headers_for, create_test_user

if TYPE_CHECKING:
    from fastapi import FastAPI
    from httpx import Response

    from rag_backend.application.services.chat_stream_service import _ChatContext

NONEXISTENT_UUID = "00000000-0000-0000-0000-000000000000"
CALLER_ANON = "anon"
CALLER_OWNER = "owner"
CALLER_OTHER = "other"
CALLER_ADMIN = "admin"
STREAM = "POST /{id}/chat/stream"
CHAT = "POST /{id}/chat"
GET_ONE = "GET /{id}"
GET_MESSAGES = "GET /{id}/messages"
GENERATE_TITLE = "POST /{id}/generate-title"
DELETE = "DELETE /{id}"


class _FixedTokenAgent:
    """Deterministic agent: one token, then the stream service completes."""

    async def chat(self, ctx: _ChatContext) -> AsyncIterator[dict[str, object]]:
        del ctx
        yield {"type": "token", "content": "Hello"}
        yield {"type": "complete", "content": "Hello"}


@dataclass
class OwnershipEnv:
    """App + one conversation per owner type, and a client per caller."""

    app: FastAPI
    users: dict[str, User]
    owner_conversation_id: str

    def client(self, caller: str) -> AsyncClient:
        """An HTTP client signed in as ``caller`` (no headers for anon)."""
        user = self.users.get(caller)
        headers = auth_headers_for(user) if user is not None else {}
        return AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url="https://test/api/conversations",
            headers=headers,
        )


async def _fixed_title(_messages: list[dict[str, str]]) -> str:
    """Deterministic title generator (no LLM)."""
    return "Fixed title"


def patch_agents(monkeypatch: pytest.MonkeyPatch) -> None:
    from rag_backend.api.routes import chat_stream as stream_module
    from rag_backend.api.routes import conversations as conv_module

    agent = MagicMock()
    agent.chat = _FixedTokenAgent().chat
    monkeypatch.setattr(
        stream_module, "build_alter_ego_agent", lambda _db, _c, _scope: agent
    )
    monkeypatch.setattr(
        conv_module, "build_agent_for_conversation", lambda _conv, _db, _c: agent
    )


def reset_rate_limits() -> None:
    """Every row is a fresh caller; the per-IP chat limit must not leak across rows."""
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()


@asynccontextmanager
async def ownership_env(tmp_path: Path) -> AsyncIterator[OwnershipEnv]:
    """File-backed SQLite app with owner/other/admin users and an owner conversation."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.api.dependencies.conversation import (
        get_conversation_title_generator,
    )
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'ownership.db'}", echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    users = {
        CALLER_OWNER: await create_test_user("owner@own.test", UserRole.EDITOR),
        CALLER_OTHER: await create_test_user("other@own.test", UserRole.EDITOR),
        CALLER_ADMIN: await create_test_user("admin@own.test", UserRole.ADMIN),
    }
    app = create_app()
    app.dependency_overrides[get_conversation_title_generator] = lambda: _fixed_title
    probe = OwnershipEnv(app=app, users=users, owner_conversation_id="")
    async with probe.client(CALLER_OWNER) as owner:
        created = await owner.post("", json={"title": "Private"})
    assert created.status_code == 201
    try:
        yield OwnershipEnv(
            app=app, users=users, owner_conversation_id=created.json()["id"]
        )
    finally:
        db_config.c_engine = None
        await close_db()
        await engine.dispose()


async def call_endpoint(
    client: AsyncClient, endpoint: str, conversation_id: str
) -> Response:
    """Send ``endpoint`` for ``conversation_id`` and return the response."""
    path = f"/{conversation_id}"
    body = {"content": "Hello"}
    if endpoint == STREAM:
        return await client.post(f"{path}/chat/stream", json=body)
    if endpoint == CHAT:
        return await client.post(f"{path}/chat", json=body)
    if endpoint == GET_ONE:
        return await client.get(path)
    if endpoint == GET_MESSAGES:
        return await client.get(f"{path}/messages")
    if endpoint == GENERATE_TITLE:
        return await client.post(f"{path}/generate-title")
    return await client.delete(path)
