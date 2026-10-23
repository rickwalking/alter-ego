"""Both chat routes read personal knowledge only in the site owner's conversations."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient

from rag_backend.agents.chat_knowledge import (
    OWNER_KNOWLEDGE,
    PUBLIC_KNOWLEDGE,
    KnowledgeScope,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.container import get_container
from tests.integration.conversation_access_support import (
    CALLER_ADMIN,
    CALLER_ANON,
    CALLER_OTHER,
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


class _SiteOwner:
    """Sets the configured site owner (``AUTOPILOT_OWNER_USER_ID``) for a test."""

    def set(self, user_id: str) -> None:
        settings = get_settings().model_copy(
            update={"autopilot_owner_user_id": user_id}
        )
        get_container().settings.override(settings)


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    reset_rate_limits()


@pytest.fixture
def site_owner() -> Iterator[_SiteOwner]:
    yield _SiteOwner()
    get_container().settings.reset_override()


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


async def _own_conversation(client: AsyncClient) -> str:
    created = await client.post("", json={"title": "Mine"})
    assert created.status_code == 201
    return str(created.json()["id"])


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [STREAM, CHAT])
async def test_anonymous_conversation_reads_public_knowledge_only(
    env: OwnershipEnv, recorder: _Recorder, site_owner: _SiteOwner, endpoint: str
) -> None:
    """Scenario: Both chat routes pick the scope from the conversation owner"""
    site_owner.set(str(env.users[CALLER_OWNER].id))
    async with env.client(CALLER_ANON) as visitor:
        conversation_id = await _own_conversation(visitor)
        response = await call_endpoint(visitor, endpoint, conversation_id)

    assert response.status_code == 200
    assert recorder.scopes == [PUBLIC_KNOWLEDGE]


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [STREAM, CHAT])
async def test_site_owner_conversation_reads_personal_and_public_knowledge(
    env: OwnershipEnv, recorder: _Recorder, site_owner: _SiteOwner, endpoint: str
) -> None:
    """Scenario: The owner's chat reads personal and public knowledge"""
    site_owner.set(str(env.users[CALLER_OWNER].id))
    async with env.client(CALLER_OWNER) as owner:
        response = await call_endpoint(owner, endpoint, env.owner_conversation_id)

    assert response.status_code == 200
    assert recorder.scopes == [OWNER_KNOWLEDGE]


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [STREAM, CHAT])
@pytest.mark.parametrize("caller", [CALLER_OTHER, CALLER_ADMIN])
async def test_editor_and_other_admin_conversations_read_public_knowledge_only(
    env: OwnershipEnv,
    recorder: _Recorder,
    site_owner: _SiteOwner,
    endpoint: str,
    caller: str,
) -> None:
    """Scenario: An editor's or another admin's chat reads public knowledge only"""
    site_owner.set(str(env.users[CALLER_OWNER].id))
    async with env.client(caller) as client:
        conversation_id = await _own_conversation(client)
        response = await call_endpoint(client, endpoint, conversation_id)

    assert response.status_code == 200
    assert recorder.scopes == [PUBLIC_KNOWLEDGE]


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [STREAM, CHAT])
async def test_without_a_site_owner_the_owner_reads_public_knowledge_only(
    env: OwnershipEnv, recorder: _Recorder, site_owner: _SiteOwner, endpoint: str
) -> None:
    """Scenario: Without a configured site owner every chat reads public knowledge only"""
    site_owner.set("")
    async with env.client(CALLER_OWNER) as owner:
        response = await call_endpoint(owner, endpoint, env.owner_conversation_id)

    assert response.status_code == 200
    assert recorder.scopes == [PUBLIC_KNOWLEDGE]
