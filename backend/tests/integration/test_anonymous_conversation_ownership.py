"""Anonymous conversations accept writes only from the visitor holding their token.

Feature file: tests/features/anonymous_conversation_ownership.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import timedelta
from pathlib import Path

import jwt
import pytest
import pytest_asyncio
from httpx import AsyncClient

from rag_backend.api.constants import ERR_CONVERSATION_NOT_FOUND
from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_ANON
from rag_backend.infrastructure.auth import create_anonymous_token
from rag_backend.infrastructure.config.settings import get_settings
from tests.integration.conversation_access_support import (
    CALLER_ANON,
    CALLER_OTHER,
    CHAT,
    STREAM,
    OwnershipEnv,
    call_endpoint,
    ownership_env,
    patch_agents,
    reset_rate_limits,
)

ANON_COOKIE = "anon_token"


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    reset_rate_limits()


@pytest_asyncio.fixture
async def env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[OwnershipEnv]:
    """The shared app with agents patched (see conversation_access_support)."""
    patch_agents(monkeypatch)
    async with ownership_env(tmp_path) as built:
        yield built


async def _visitor_conversation(visitor: AsyncClient) -> str:
    """Create an anonymous conversation; the client keeps its anon_token."""
    created = await visitor.post("", json={"title": "Visitor"})
    assert created.status_code == 201
    assert ANON_COOKIE in created.headers.get("set-cookie", "")
    return str(created.json()["id"])


async def _saved_messages(conversation_id: str) -> int:
    """Messages persisted in ``conversation_id`` (read straight from the DB)."""
    from uuid import UUID

    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.conversation_repository import (
        PostgresMessageRepository,
    )

    async with get_session_maker()() as session:
        repo = PostgresMessageRepository(session)
        return await repo.count_by_conversation(UUID(conversation_id))


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [STREAM, CHAT])
async def test_visitor_chats_in_their_own_conversation(
    env: OwnershipEnv, endpoint: str
) -> None:
    """The visitor who created the conversation can keep writing into it."""
    # Scenario: The visitor keeps chatting in the conversation they created
    async with env.client(CALLER_ANON) as visitor:
        conversation_id = await _visitor_conversation(visitor)
        resp = await call_endpoint(visitor, endpoint, conversation_id)
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [STREAM, CHAT])
async def test_other_visitor_gets_404(env: OwnershipEnv, endpoint: str) -> None:
    """Visitor B's token names B's conversation, not A's."""
    # Scenario: Another visitor cannot write into someone else's anonymous conversation
    async with env.client(CALLER_ANON) as visitor_a:
        conversation_a = await _visitor_conversation(visitor_a)
        async with env.client(CALLER_ANON) as visitor_b:
            await _visitor_conversation(visitor_b)
            resp = await call_endpoint(visitor_b, endpoint, conversation_a)
    assert resp.status_code == 404
    assert resp.json()["detail"] == ERR_CONVERSATION_NOT_FOUND
    assert await _saved_messages(conversation_a) == 0


@pytest.mark.asyncio
async def test_signed_in_user_without_token_gets_404(env: OwnershipEnv) -> None:
    """Signing in does not open somebody's anonymous conversation."""
    # Scenario: A signed-in user cannot write into an anonymous conversation
    async with env.client(CALLER_ANON) as visitor:
        conversation_id = await _visitor_conversation(visitor)
    async with env.client(CALLER_OTHER) as other:
        resp = await call_endpoint(other, STREAM, conversation_id)
    assert resp.status_code == 404


def _expired_token(conversation_id: str) -> str:
    return create_anonymous_token(
        get_settings(), conversation_id, expires_delta=timedelta(minutes=-1)
    )


def _foreign_key_token(conversation_id: str) -> str:
    payload = {
        "sub": f"anon:{conversation_id}",
        "conversation_id": conversation_id,
        "type": JWT_TYPE_ANON,
    }
    return jwt.encode(
        payload, "not-the-server-key-not-the-server-key", algorithm=JWT_ALGORITHM
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("make_token", [None, _expired_token, _foreign_key_token])
async def test_missing_expired_or_tampered_token_gets_404(
    env: OwnershipEnv, make_token: Callable[[str], str] | None
) -> None:
    """Only a valid, unexpired token signed by the server opens the conversation."""
    # Scenario: A missing, expired or tampered token is rejected
    async with env.client(CALLER_ANON) as visitor:
        conversation_id = await _visitor_conversation(visitor)
    async with env.client(CALLER_ANON) as caller:
        if make_token is not None:
            caller.cookies.set(ANON_COOKIE, make_token(conversation_id))
        resp = await call_endpoint(caller, STREAM, conversation_id)
    assert resp.status_code == 404
    assert await _saved_messages(conversation_id) == 0


@pytest.mark.asyncio
async def test_second_conversation_keeps_the_first_one_writable(
    env: OwnershipEnv,
) -> None:
    """Each conversation has its own token cookie, so a second tab does not lock the first."""
    # Scenario: A visitor with two open conversations can write into both
    async with env.client(CALLER_ANON) as visitor:
        first = await _visitor_conversation(visitor)
        second = await _visitor_conversation(visitor)
        first_resp = await call_endpoint(visitor, STREAM, first)
        second_resp = await call_endpoint(visitor, STREAM, second)
    assert first_resp.status_code == 200
    assert second_resp.status_code == 200


@pytest.mark.asyncio
async def test_token_in_the_url_is_not_a_credential(env: OwnershipEnv) -> None:
    """A token passed as ``?token=`` (loggable, leaks via referrers) opens nothing."""
    # Scenario: A missing, expired or tampered token is rejected
    async with env.client(CALLER_ANON) as visitor:
        conversation_id = await _visitor_conversation(visitor)
    token = create_anonymous_token(get_settings(), conversation_id)
    async with env.client(CALLER_ANON) as caller:
        resp = await caller.post(
            f"/{conversation_id}/chat/stream",
            params={"token": token},
            json={"content": "Hello"},
        )
    assert resp.status_code == 404
    assert await _saved_messages(conversation_id) == 0


@pytest.mark.asyncio
async def test_signed_in_user_with_another_conversations_token_gets_404(
    env: OwnershipEnv,
) -> None:
    """A valid token for conversation B does not open conversation A, signed in or not."""
    # Scenario: A signed-in user cannot write into an anonymous conversation
    async with env.client(CALLER_ANON) as visitor:
        conversation_a = await _visitor_conversation(visitor)
    token_b = create_anonymous_token(
        get_settings(), "11111111-1111-1111-1111-111111111111"
    )
    async with env.client(CALLER_OTHER) as other:
        other.cookies.set(ANON_COOKIE, token_b)
        resp = await call_endpoint(other, STREAM, conversation_a)
    assert resp.status_code == 404
    assert await _saved_messages(conversation_a) == 0


@pytest.mark.asyncio
async def test_an_older_site_wide_token_does_not_hide_the_scoped_one(
    env: OwnershipEnv,
) -> None:
    """A leftover token for another conversation, sent along, does not block this one."""
    # Scenario: A visitor with two open conversations can write into both
    async with env.client(CALLER_ANON) as visitor:
        conversation_id = await _visitor_conversation(visitor)
        scoped = create_anonymous_token(get_settings(), conversation_id)
        leftover = create_anonymous_token(
            get_settings(), "22222222-2222-2222-2222-222222222222"
        )
    async with env.client(CALLER_ANON) as browser:
        resp = await browser.post(
            f"/{conversation_id}/chat/stream",
            json={"content": "Hello"},
            headers={"cookie": f"{ANON_COOKIE}={scoped}; {ANON_COOKIE}={leftover}"},
        )
    assert resp.status_code == 200
