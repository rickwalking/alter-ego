"""Both chat routes give an anonymous conversation public knowledge only."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient

from rag_backend.agents.alter_ego_knowledge import (
    OWNER_KNOWLEDGE,
    PUBLIC_KNOWLEDGE,
    KnowledgeScope,
)
from tests.integration.conversation_access_support import (
    CALLER_ANON,
    CALLER_OWNER,
    CHAT,
    STREAM,
    OwnershipEnv,
    call_endpoint,
    ownership_env,
    reset_rate_limits,
)


class _Recorder:
    """Stands in for ``build_alter_ego_agent`` and keeps the scopes it was given."""

    def __init__(self) -> None:
        self.scopes: list[KnowledgeScope] = []

    def build(
        self, _db: object, _container: object, scope: KnowledgeScope
    ) -> MagicMock:
        self.scopes.append(scope)
        agent = MagicMock()
        agent.chat = _reply
        return agent


async def _reply(_ctx: object) -> AsyncIterator[dict[str, object]]:
    yield {"type": "token", "content": "Hello"}
    yield {"type": "complete", "content": "Hello"}


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    reset_rate_limits()


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    from rag_backend.api.dependencies import agents as agents_module
    from rag_backend.api.routes import chat_stream as stream_module

    recorded = _Recorder()
    monkeypatch.setattr(stream_module, "build_alter_ego_agent", recorded.build)
    monkeypatch.setattr(agents_module, "build_alter_ego_agent", recorded.build)
    return recorded


@pytest_asyncio.fixture
async def env(tmp_path: Path, recorder: _Recorder) -> AsyncIterator[OwnershipEnv]:
    async with ownership_env(tmp_path) as built:
        yield built


async def _visitor_conversation(visitor: AsyncClient) -> str:
    created = await visitor.post("", json={"title": "Visitor"})
    assert created.status_code == 201
    return str(created.json()["id"])


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [STREAM, CHAT])
async def test_anonymous_conversation_reads_public_knowledge_only(
    env: OwnershipEnv, recorder: _Recorder, endpoint: str
) -> None:
    """Scenario: Both chat routes pick the scope from the conversation owner"""
    async with env.client(CALLER_ANON) as visitor:
        conversation_id = await _visitor_conversation(visitor)
        response = await call_endpoint(visitor, endpoint, conversation_id)

    assert response.status_code == 200
    assert recorder.scopes == [PUBLIC_KNOWLEDGE]


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [STREAM, CHAT])
async def test_owner_conversation_reads_personal_and_public_knowledge(
    env: OwnershipEnv, recorder: _Recorder, endpoint: str
) -> None:
    """Scenario: The owner's chat reads personal and public knowledge"""
    async with env.client(CALLER_OWNER) as owner:
        response = await call_endpoint(owner, endpoint, env.owner_conversation_id)

    assert response.status_code == 200
    assert recorder.scopes == [OWNER_KNOWLEDGE]
