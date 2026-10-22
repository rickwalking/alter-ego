"""Conversation ownership across every conversation endpoint.

Feature file: tests/features/conversation_ownership.feature

Table-driven: each row is (endpoint, caller) -> expected status for a
conversation owned by a signed-in editor. Anonymous callers, other users and
unknown ids all get the same 404 so a conversation's existence never leaks.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

from rag_backend.api.constants import ERR_CONVERSATION_NOT_FOUND
from tests.integration.conversation_access_support import (
    CALLER_ADMIN,
    CALLER_ANON,
    CALLER_OTHER,
    CALLER_OWNER,
    CHAT,
    DELETE,
    GENERATE_TITLE,
    GET_MESSAGES,
    GET_ONE,
    NONEXISTENT_UUID,
    STREAM,
    OwnershipEnv,
    call_endpoint,
    ownership_env,
    patch_agents,
    reset_rate_limits,
)


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    reset_rate_limits()


@pytest_asyncio.fixture
async def env(tmp_path: Path) -> AsyncIterator[OwnershipEnv]:
    """The shared app with an owner conversation (see conversation_access_support)."""
    async with ownership_env(tmp_path) as built:
        yield built


async def _owner_message_count(env: OwnershipEnv) -> int:
    async with env.client(CALLER_OWNER) as owner:
        resp = await owner.get(f"/{env.owner_conversation_id}/messages")
    assert resp.status_code == 200
    return len(resp.json()["items"])


# Scenario: Anonymous caller cannot stream into a signed-in user's conversation
# Scenario: Another user cannot stream into someone else's conversation
# Scenario: Anonymous caller cannot use the non-streaming chat on a signed-in user's conversation
# Scenario: Another user cannot read or delete someone else's conversation
DENIED_ROWS = [
    (STREAM, CALLER_ANON),
    (STREAM, CALLER_OTHER),
    (CHAT, CALLER_ANON),
    (CHAT, CALLER_OTHER),
    (GET_ONE, CALLER_OTHER),
    (GET_MESSAGES, CALLER_OTHER),
    (GENERATE_TITLE, CALLER_OTHER),
    (DELETE, CALLER_OTHER),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("endpoint", "caller"), DENIED_ROWS)
async def test_non_owner_gets_404_and_changes_nothing(
    env: OwnershipEnv, monkeypatch: pytest.MonkeyPatch, endpoint: str, caller: str
) -> None:
    """A non-owner gets 404 "Conversation not found" and the conversation is untouched."""
    patch_agents(monkeypatch)
    async with env.client(caller) as client:
        resp = await call_endpoint(client, endpoint, env.owner_conversation_id)
    assert resp.status_code == 404
    assert ERR_CONVERSATION_NOT_FOUND in resp.text
    assert await _owner_message_count(env) == 0


# Scenario: Owner and admin can stream into the owner's conversation
ALLOWED_ROWS = [
    (STREAM, CALLER_OWNER, 200),
    (STREAM, CALLER_ADMIN, 200),
    (CHAT, CALLER_OWNER, 200),
    (CHAT, CALLER_ADMIN, 200),
    (GENERATE_TITLE, CALLER_OWNER, 200),
    (GENERATE_TITLE, CALLER_ADMIN, 200),
    (GET_ONE, CALLER_OWNER, 200),
    (GET_ONE, CALLER_ADMIN, 200),
    (GET_MESSAGES, CALLER_OWNER, 200),
    (GET_MESSAGES, CALLER_ADMIN, 200),
    (DELETE, CALLER_OWNER, 204),
    (DELETE, CALLER_ADMIN, 204),
    (GET_ONE, CALLER_ANON, 401),
    (GET_MESSAGES, CALLER_ANON, 401),
    (DELETE, CALLER_ANON, 401),
    (GENERATE_TITLE, CALLER_ANON, 401),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("endpoint", "caller", "expected"), ALLOWED_ROWS)
async def test_owner_admin_and_anonymous_reads(
    env: OwnershipEnv,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    caller: str,
    expected: int,
) -> None:
    """Owner and admin reach the conversation; anonymous reads stay 401."""
    patch_agents(monkeypatch)
    async with env.client(caller) as client:
        resp = await call_endpoint(client, endpoint, env.owner_conversation_id)
    assert resp.status_code == expected


@pytest.mark.asyncio
async def test_owner_stream_persists_both_turns(
    env: OwnershipEnv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The owner's stream returns SSE tokens and persists user + assistant turns."""
    # Scenario: Owner and admin can stream into the owner's conversation
    patch_agents(monkeypatch)
    async with env.client(CALLER_OWNER) as owner:
        resp = await owner.post(
            f"/{env.owner_conversation_id}/chat/stream", json={"content": "Hi"}
        )
    assert resp.status_code == 200
    assert '"type": "token"' in resp.text or '"type":"token"' in resp.text
    assert await _owner_message_count(env) == 2


@pytest.mark.asyncio
async def test_foreign_conversation_not_listed(env: OwnershipEnv) -> None:
    """Another user's list never contains the owner's conversation."""
    # Scenario: Another user's conversation list does not include the owner's conversation
    async with env.client(CALLER_OTHER) as other:
        resp = await other.get("")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert env.owner_conversation_id not in ids


@pytest.mark.asyncio
async def test_foreign_delete_keeps_conversation(env: OwnershipEnv) -> None:
    """A rejected delete leaves the conversation readable by its owner."""
    # Scenario: Another user cannot read or delete someone else's conversation
    async with env.client(CALLER_OTHER) as other:
        resp = await other.delete(f"/{env.owner_conversation_id}")
    assert resp.status_code == 404
    async with env.client(CALLER_OWNER) as owner:
        assert (await owner.get(f"/{env.owner_conversation_id}")).status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("caller", [CALLER_ANON, CALLER_OTHER])
async def test_unknown_and_foreign_ids_look_the_same(
    env: OwnershipEnv, monkeypatch: pytest.MonkeyPatch, caller: str
) -> None:
    """The stream answers an unknown id and a foreign id with the same 404 body."""
    # Scenario: Unknown conversation answers the same 404 as a foreign one
    patch_agents(monkeypatch)
    body = {"content": "Hello"}
    async with env.client(caller) as client:
        unknown = await client.post(f"/{NONEXISTENT_UUID}/chat/stream", json=body)
        foreign = await client.post(
            f"/{env.owner_conversation_id}/chat/stream", json=body
        )
    assert unknown.status_code == foreign.status_code == 404
    assert unknown.json() == foreign.json()
    assert ERR_CONVERSATION_NOT_FOUND in str(unknown.json())


@pytest.mark.asyncio
async def test_anonymous_visitor_streams_into_anonymous_conversation(
    env: OwnershipEnv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An anonymous conversation stays open to the anonymous stream."""
    # Scenario: Anonymous visitor keeps chatting in an anonymous conversation
    patch_agents(monkeypatch)
    async with env.client(CALLER_ANON) as anon:
        created = await anon.post("", json={"title": "Visitor"})
        conversation_id = created.json()["id"]
        resp = await anon.post(
            f"/{conversation_id}/chat/stream", json={"content": "Hello"}
        )
    assert created.status_code == 201
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_other_user_publish_chat_is_404(env: OwnershipEnv) -> None:
    """Another user's carousel conversation answers 404 on the publish chat too."""
    # Scenario: User tries to access another user's publish chat
    from uuid import UUID, uuid4

    from rag_backend.domain.constants.conversation import (
        CONVERSATION_METADATA_PROJECT_ID,
    )
    from rag_backend.domain.models import Conversation
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.conversation_repository import (
        PostgresConversationRepository,
    )

    async with get_session_maker()() as session:
        conversation = await PostgresConversationRepository(session).create(
            Conversation(
                title="Carousel chat",
                user_id=UUID(str(env.users[CALLER_OWNER].id)),
                metadata={CONVERSATION_METADATA_PROJECT_ID: str(uuid4())},
            )
        )
        await session.commit()
    async with env.client(CALLER_OTHER) as other:
        resp = await other.post(
            f"/{conversation.id}/publish-chat/stream", json={"content": "Hi"}
        )
    assert resp.status_code == 404
    assert resp.json()["detail"] == ERR_CONVERSATION_NOT_FOUND


@pytest.mark.asyncio
async def test_signed_in_user_cannot_read_anonymous_conversation(
    env: OwnershipEnv,
) -> None:
    """An anonymous conversation has no owner, so no signed-in reader gets it."""
    # Scenario: Another user cannot read or delete someone else's conversation
    async with env.client(CALLER_ANON) as anon:
        created = await anon.post("", json={"title": "Visitor"})
    async with env.client(CALLER_OTHER) as other:
        resp = await other.get(f"/{created.json()['id']}/messages")
    assert resp.status_code == 404
    assert resp.json()["detail"] == ERR_CONVERSATION_NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint", [CHAT, GET_ONE, GET_MESSAGES, GENERATE_TITLE, DELETE]
)
async def test_every_endpoint_hides_a_foreign_id_like_an_unknown_one(
    env: OwnershipEnv, monkeypatch: pytest.MonkeyPatch, endpoint: str
) -> None:
    """Another user cannot tell a foreign conversation from a missing one."""
    # Scenario: Unknown conversation answers the same 404 as a foreign one
    patch_agents(monkeypatch)
    async with env.client(CALLER_OTHER) as other:
        unknown = await call_endpoint(other, endpoint, NONEXISTENT_UUID)
        foreign = await call_endpoint(other, endpoint, env.owner_conversation_id)
    assert unknown.status_code == foreign.status_code == 404
    assert unknown.json() == foreign.json()
