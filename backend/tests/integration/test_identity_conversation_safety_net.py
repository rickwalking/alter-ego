"""Identity + Conversation byte-identical safety-net tests (AE-0097).

Behavioral + golden-snapshot safety net for the Phase 3 Identity/Conversation
extraction. Every behavior test asserts the /api auth, admin, or conversation
contract that the relocation (AE-0099 / AE-0101 / AE-0102) must preserve. The
golden snapshots capture the deterministic baseline INCLUDING Set-Cookie
attributes (access_token / anon_token: httponly/secure/samesite/max-age), the
``X-Agent-Origin`` header, and the HS256 JWT shape. The SSE stream tests use a
DETERMINISTIC mock agent and assert event TYPES in order + ``id:``/``data:``
framing + Last-Event-ID resume (never a raw byte diff of LLM content).

Feature files:
- tests/features/auth.feature
- tests/features/admin.feature
- tests/features/conversations.feature
- tests/features/alter_ego_chat_sse.feature (SSE framing/resume scenarios)

Run with ``--snapshot-update`` (flag registered in tests/conftest.py) to
regenerate the committed golden snapshots from current, pre-refactor behavior.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator, AsyncIterator
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from rag_backend.application.services.chat_stream_service import _ChatContext
from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_ANON, JWT_TYPE_AUTH
from rag_backend.domain.models import User, UserRole
from rag_backend.infrastructure.auth import hash_password
from tests.integration.conftest import TEST_SECRET, auth_headers_for, create_test_user
from tests.snapshots.conversation import _snapshot as conv_snapshot
from tests.snapshots.identity import _snapshot as id_snapshot

if TYPE_CHECKING:
    from fastapi import FastAPI
    from httpx import Response
    from sqlalchemy.ext.asyncio import AsyncEngine

# --- Constants -----------------------------------------------------------------
NONEXISTENT_UUID = "00000000-0000-0000-0000-000000000000"
SNAPSHOT_UPDATE_OPTION = "--snapshot-update"
ANON_SECRET = "test-anon-secret-for-integration-tests"
ADMIN_EMAIL = "id-admin@integration.example.com"
EDITOR_EMAIL = "id-editor@integration.example.com"
LOGIN_PASSWORD = "SecurePass123!"
NEW_PASSWORD = "NewSecurePass456!"
COOKIE_ACCESS = "access_token"
COOKIE_ANON = "anon_token"
SSE_EVENT_TYPES = ("token", "sources", "complete", "error", "tool_result")


@pytest.fixture
def snapshot_update(request: pytest.FixtureRequest) -> bool:
    """Whether snapshots should be written instead of asserted."""
    return bool(request.config.getoption(SNAPSHOT_UPDATE_OPTION))


# --- Engine / app factory ------------------------------------------------------
async def _make_engine(db_path: str) -> AsyncEngine:
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.infrastructure.database.config import Base

    # A file-backed SQLite DB (not ``:memory:``) so multiple, possibly
    # overlapping sessions — the auth dependency's session and the route's own
    # nested ``get_session`` used by change-password / reset-password — all see
    # the same data. A per-connection ``:memory:`` DB cannot do this.
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    return engine


async def _create_user_with_password(email: str, role: UserRole, password: str) -> User:
    """Persist a user whose bcrypt hash matches ``password`` (for login flows)."""
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = PostgresUserRepository(session)
        user = User(
            email=email,
            full_name=email.split("@")[0].title(),
            role=role,
            hashed_password=hash_password(password),
        )
        created = await repo.create(user)
        await session.commit()
        return created


class IdEnv:
    """Test environment: app + clients + seeding helpers (see id_env fixture)."""

    def __init__(self, app: FastAPI, admin: User, editor: User) -> None:
        self._app = app
        self.admin = admin
        self.editor = editor

    def client_for(self, user: User) -> AsyncClient:
        transport = ASGITransport(app=self._app)
        return AsyncClient(
            transport=transport,
            base_url="http://test",
            headers=auth_headers_for(user),
        )

    def anon_client(self) -> AsyncClient:
        transport = ASGITransport(app=self._app)
        return AsyncClient(transport=transport, base_url="http://test")

    async def make_user(self, email: str, role: UserRole) -> User:
        return await create_test_user(email, role)


@pytest_asyncio.fixture
async def id_env(tmp_path: object) -> AsyncGenerator[IdEnv, None]:
    """Shared file-backed DB + app with an admin + editor and client helpers."""
    from pathlib import Path

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.database.config import close_db

    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = ANON_SECRET

    assert isinstance(tmp_path, Path)
    db_path = str(tmp_path / "id_env.db")
    engine = await _make_engine(db_path)
    admin = await _create_user_with_password(
        ADMIN_EMAIL, UserRole.ADMIN, LOGIN_PASSWORD
    )
    editor = await _create_user_with_password(
        EDITOR_EMAIL, UserRole.EDITOR, LOGIN_PASSWORD
    )
    app = create_app()
    env = IdEnv(app=app, admin=admin, editor=editor)
    try:
        yield env
    finally:
        db_config.c_engine = None
        await close_db()
        await engine.dispose()


# --- Deterministic mock chat agent ---------------------------------------------
class _FixedTokenAgent:
    """Deterministic chat agent yielding a fixed token/sources/complete sequence.

    Used to make the SSE stream falsifiable WITHOUT a live LLM: the event TYPES,
    order, and content are fixed, so a reordered or renamed event breaks the
    assertion. Never constructs any external (Pinecone/OpenAI) client.
    """

    async def chat(self, ctx: _ChatContext) -> AsyncIterator[dict[str, object]]:
        del ctx
        yield {"type": "token", "content": "Hello"}
        yield {"type": "token", "content": " world"}
        yield {
            "type": "sources",
            "content": [
                {
                    "document_id": "11111111-1111-1111-1111-111111111111",
                    "document_title": "Fixture Source",
                    "content": "fixture",
                    "score": 0.5,
                }
            ],
        }


def _mock_agent() -> MagicMock:
    agent = MagicMock()
    agent.chat = _FixedTokenAgent().chat
    return agent


def _patch_agents(monkeypatch: pytest.MonkeyPatch) -> None:
    """Override agent builders at the app edge with the deterministic stub."""
    from rag_backend.api.routes import chat_stream as stream_module
    from rag_backend.api.routes import conversations as conv_module

    agent = _mock_agent()
    monkeypatch.setattr(stream_module, "build_alter_ego_agent", lambda _db, _c: agent)
    monkeypatch.setattr(
        conv_module, "build_agent_for_conversation", lambda _conv, _db, _c: agent
    )


# --- SSE parsing helpers -------------------------------------------------------
def _parse_sse(text: str) -> list[tuple[int | None, dict[str, object]]]:
    """Parse raw SSE text into ``(id, data)`` pairs, ignoring keep-alive pings.

    Keep-alive comments (lines starting with ``:``) are dropped so ping
    interleaving never affects the asserted event sequence.
    """
    events: list[tuple[int | None, dict[str, object]]] = []
    event_id: int | None = None
    data = ""
    for line in text.split("\n"):
        if line.startswith("id: "):
            event_id = int(line[4:])
        elif line.startswith("data: "):
            data += line[6:]
        elif line == "":
            if data:
                events.append((event_id, json.loads(data)))
            event_id = None
            data = ""
    return events


def _event_types(events: list[tuple[int | None, dict[str, object]]]) -> list[str]:
    return [str(data.get("type")) for _id, data in events]


# ==============================================================================
# Auth behavior scenarios (tests/features/auth.feature)
# ==============================================================================
class TestAuthBehavior:
    """login / logout / me / change-password contract."""

    @pytest.mark.asyncio
    async def test_login_sets_access_token_cookie(self, id_env: IdEnv) -> None:
        """Scenario: Successful login returns JWT cookie."""
        async with id_env.anon_client() as client:
            resp = await client.post(
                "/api/auth/token",
                json={"email": ADMIN_EMAIL, "password": LOGIN_PASSWORD},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        decoded = jwt.decode(
            body["access_token"], TEST_SECRET, algorithms=[JWT_ALGORITHM]
        )
        assert decoded["type"] == JWT_TYPE_AUTH
        assert decoded["email"] == ADMIN_EMAIL
        set_cookie = resp.headers["set-cookie"]
        assert COOKIE_ACCESS in set_cookie
        assert "httponly" in set_cookie.lower()
        assert "samesite=strict" in set_cookie.lower()

    @pytest.mark.asyncio
    async def test_login_invalid_credentials_rejected(self, id_env: IdEnv) -> None:
        """Scenario: Invalid credentials are rejected."""
        async with id_env.anon_client() as client:
            resp = await client.post(
                "/api/auth/token",
                json={"email": ADMIN_EMAIL, "password": "wrongpassword"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token_fails(self, id_env: IdEnv) -> None:
        """Scenario: Accessing a protected endpoint without a token fails."""
        async with id_env.anon_client() as client:
            resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me(self, id_env: IdEnv) -> None:
        """Scenario: Get current user information."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.get("/api/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == ADMIN_EMAIL
        assert body["role"] == "admin"

    @pytest.mark.asyncio
    async def test_logout_clears_cookie(self, id_env: IdEnv) -> None:
        """Scenario: Logout clears the access_token cookie."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.post("/api/auth/logout")
        assert resp.status_code == 204
        assert COOKIE_ACCESS in resp.headers["set-cookie"]

    @pytest.mark.asyncio
    async def test_change_password_current_behavior(self, id_env: IdEnv) -> None:
        """Scenario: Change own password — captures CURRENT behavior.

        DISCOVERED DEFECT (AE-0097 finding, reported, NOT fixed here — TESTS-ONLY
        ticket, no src change): ``change_password`` reloads the user, sets
        ``hashed_password`` (which does NOT bump ``updated_at``), then calls
        ``PostgresUserRepository.update``. The ``users.updated_at`` column has
        ``onupdate=func.now()``; because the entity's ``updated_at`` is unchanged
        the UPDATE applies the server-side default, which EXPIRES the column. The
        subsequent ``UserModel.to_entity()`` then triggers a synchronous lazy
        reload inside the async route → ``SQLAlchemyError`` (MissingGreenlet) →
        500. ``admin.update_user`` avoids this because ``set_role``/``activate``
        bump ``updated_at`` to an explicit value (no server onupdate, no expiry).

        This test LOCKS that deterministic 500 so the Phase-3 refactor diffs
        against the true current contract (snapshot diff=0). When the underlying
        defect is fixed, update this scenario to the intended 204 + re-login.
        """
        async with id_env.client_for(id_env.editor) as client:
            resp = await client.post(
                "/api/auth/change-password",
                json={
                    "current_password": LOGIN_PASSWORD,
                    "new_password": NEW_PASSWORD,
                },
            )
        assert resp.status_code == 500

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, id_env: IdEnv) -> None:
        """Scenario: Change password rejects a wrong current password.

        The wrong-password guard runs BEFORE the defective update path, so this
        deterministically returns 401 (the intended contract).
        """
        async with id_env.client_for(id_env.editor) as client:
            resp = await client.post(
                "/api/auth/change-password",
                json={"current_password": "nope", "new_password": NEW_PASSWORD},
            )
        assert resp.status_code == 401


# ==============================================================================
# Admin user-management scenarios (tests/features/admin.feature)
# ==============================================================================
class TestAdminBehavior:
    """Admin user CRUD + role assignment contract."""

    @pytest.mark.asyncio
    async def test_create_user_auto_password(self, id_env: IdEnv) -> None:
        """Scenario: Admin creates a new user with auto-generated password."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.post(
                "/api/admin/users",
                json={
                    "email": "new1@integration.example.com",
                    "full_name": "New Editor",
                    "role": "editor",
                },
            )
        assert resp.status_code == 201
        assert resp.json()["temp_password"]

    @pytest.mark.asyncio
    async def test_create_user_specific_password(self, id_env: IdEnv) -> None:
        """Scenario: Admin creates user with specific password (no temp)."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.post(
                "/api/admin/users",
                json={
                    "email": "new2@integration.example.com",
                    "full_name": "Custom User",
                    "role": "editor",
                    "password": "MyCustomPass123!",
                },
            )
        assert resp.status_code == 201
        assert resp.json()["temp_password"] is None

    @pytest.mark.asyncio
    async def test_create_user_invalid_role(self, id_env: IdEnv) -> None:
        """Scenario: Admin create rejects an invalid role."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.post(
                "/api/admin/users",
                json={
                    "email": "bad@integration.example.com",
                    "full_name": "Bad Role",
                    "role": "wizard",
                },
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_non_admin_forbidden(self, id_env: IdEnv) -> None:
        """Scenario: Non-admin cannot list users."""
        async with id_env.client_for(id_env.editor) as client:
            resp = await client.get("/api/admin/users")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_user_role(self, id_env: IdEnv) -> None:
        """Scenario: Admin updates user role."""
        target = await id_env.make_user(
            "target@integration.example.com", UserRole.EDITOR
        )
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.patch(
                f"/api/admin/users/{target.id}", json={"role": "admin"}
            )
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    @pytest.mark.asyncio
    async def test_cannot_demote_last_admin(self, id_env: IdEnv) -> None:
        """Scenario: Admin cannot demote the last admin."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.patch(
                f"/api/admin/users/{id_env.admin.id}", json={"role": "editor"}
            )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_user(self, id_env: IdEnv) -> None:
        """Scenario: Admin deletes a user."""
        target = await id_env.make_user("del@integration.example.com", UserRole.EDITOR)
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.delete(f"/api/admin/users/{target.id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_cannot_delete_self(self, id_env: IdEnv) -> None:
        """Scenario: Admin cannot delete themselves."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.delete(f"/api/admin/users/{id_env.admin.id}")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_reset_password_current_behavior(self, id_env: IdEnv) -> None:
        """Scenario: Admin resets a user's password — captures CURRENT behavior.

        DISCOVERED DEFECT (AE-0097 finding, reported, NOT fixed here): identical
        root cause to ``change_password`` — ``reset_password`` sets
        ``hashed_password`` without bumping ``updated_at``, so ``repo.update``'s
        post-flush ``to_entity()`` lazy-loads the server ``onupdate`` column
        synchronously inside the async route → 500. This test LOCKS the
        deterministic 500 baseline; flip to 200 + temp_password once fixed.
        """
        target = await id_env.make_user(
            "reset@integration.example.com", UserRole.EDITOR
        )
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.post(f"/api/admin/users/{target.id}/reset-password")
        assert resp.status_code == 500

    @pytest.mark.asyncio
    async def test_update_missing_user_404(self, id_env: IdEnv) -> None:
        """Scenario: Update a non-existent user returns 404."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.patch(
                f"/api/admin/users/{NONEXISTENT_UUID}", json={"role": "editor"}
            )
        assert resp.status_code == 404


# ==============================================================================
# Conversation CRUD + non-stream chat (tests/features/conversations.feature)
# ==============================================================================
class TestConversationBehavior:
    """Conversation CRUD + non-stream chat contract."""

    @pytest.mark.asyncio
    async def test_create_conversation_authenticated(self, id_env: IdEnv) -> None:
        """Scenario: Create conversation with title (authenticated)."""
        async with id_env.client_for(id_env.editor) as client:
            resp = await client.post("/api/conversations", json={"title": "My chat"})
        assert resp.status_code == 201
        assert resp.json()["title"] == "My chat"

    @pytest.mark.asyncio
    async def test_create_conversation_anonymous_sets_anon_cookie(
        self, id_env: IdEnv
    ) -> None:
        """Scenario: Anonymous create sets the anon_token cookie + JWT."""
        async with id_env.anon_client() as client:
            resp = await client.post("/api/conversations", json={"title": "Anon chat"})
        assert resp.status_code == 201
        set_cookie = resp.headers["set-cookie"]
        assert COOKIE_ANON in set_cookie
        assert "httponly" in set_cookie.lower()
        token = client.cookies.get(COOKIE_ANON)
        assert token is not None
        decoded = jwt.decode(token, ANON_SECRET, algorithms=[JWT_ALGORITHM])
        assert decoded["type"] == JWT_TYPE_ANON

    @pytest.mark.asyncio
    async def test_list_conversations(self, id_env: IdEnv) -> None:
        """Scenario: List conversations for the authenticated user."""
        async with id_env.client_for(id_env.editor) as client:
            await client.post("/api/conversations", json={"title": "C1"})
            resp = await client.get("/api/conversations")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_conversation(self, id_env: IdEnv) -> None:
        """Scenario: Get conversation by existing ID."""
        async with id_env.client_for(id_env.editor) as client:
            created = await client.post(
                "/api/conversations", json={"title": "Readable"}
            )
            conv_id = created.json()["id"]
            resp = await client.get(f"/api/conversations/{conv_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == conv_id

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, id_env: IdEnv) -> None:
        """Scenario: Get conversation by non-existing ID."""
        async with id_env.client_for(id_env.editor) as client:
            resp = await client.get(f"/api/conversations/{NONEXISTENT_UUID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_conversation(self, id_env: IdEnv) -> None:
        """Scenario: Delete existing conversation, then it is gone."""
        async with id_env.client_for(id_env.editor) as client:
            created = await client.post(
                "/api/conversations", json={"title": "Deletable"}
            )
            conv_id = created.json()["id"]
            deleted = await client.delete(f"/api/conversations/{conv_id}")
            after = await client.get(f"/api/conversations/{conv_id}")
        assert deleted.status_code == 204
        assert after.status_code == 404

    @pytest.mark.asyncio
    async def test_get_messages_empty(self, id_env: IdEnv) -> None:
        """Scenario: Get messages for a fresh conversation."""
        async with id_env.client_for(id_env.editor) as client:
            created = await client.post("/api/conversations", json={"title": "Empty"})
            conv_id = created.json()["id"]
            resp = await client.get(f"/api/conversations/{conv_id}/messages")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    @pytest.mark.asyncio
    async def test_non_stream_chat_sets_agent_origin_header(
        self, id_env: IdEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Non-stream chat returns content + X-Agent-Origin header."""
        _patch_agents(monkeypatch)
        async with id_env.client_for(id_env.editor) as client:
            created = await client.post("/api/conversations", json={"title": "Chatty"})
            conv_id = created.json()["id"]
            resp = await client.post(
                f"/api/conversations/{conv_id}/chat", json={"content": "Hi"}
            )
        assert resp.status_code == 200
        assert resp.headers["x-agent-origin"] == "alter-ego"
        assert resp.json()["conversation_id"] == conv_id

    @pytest.mark.asyncio
    async def test_chat_empty_content_rejected(self, id_env: IdEnv) -> None:
        """Scenario: Non-stream chat rejects empty content (422)."""
        async with id_env.client_for(id_env.editor) as client:
            created = await client.post(
                "/api/conversations", json={"title": "Empty msg"}
            )
            conv_id = created.json()["id"]
            resp = await client.post(
                f"/api/conversations/{conv_id}/chat", json={"content": ""}
            )
        assert resp.status_code == 422


# ==============================================================================
# SSE stream scenarios (tests/features/alter_ego_chat_sse.feature)
# ==============================================================================
class TestChatStreamSse:
    """Deterministic SSE event-type ordering, framing, and resume."""

    async def _create_conv(self, client: AsyncClient) -> str:
        created = await client.post("/api/conversations", json={"title": "Stream"})
        assert created.status_code == 201
        return str(created.json()["id"])

    @pytest.mark.asyncio
    async def test_event_types_in_order(
        self, id_env: IdEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: stream emits token/sources... then complete, in order.

        Falsifiable: a reordered or renamed event changes this exact list.
        """
        _patch_agents(monkeypatch)
        async with id_env.anon_client() as client:
            conv_id = await self._create_conv(client)
            resp = await client.post(
                f"/api/conversations/{conv_id}/chat/stream",
                json={"content": "Hello"},
            )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        events = _parse_sse(resp.text)
        types = _event_types(events)
        assert types == ["token", "token", "sources", "complete"]
        for event_type in types:
            assert event_type in SSE_EVENT_TYPES

    @pytest.mark.asyncio
    async def test_id_and_data_framing(
        self, id_env: IdEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: every SSE event uses ``id:`` + ``data:`` framing."""
        _patch_agents(monkeypatch)
        async with id_env.anon_client() as client:
            conv_id = await self._create_conv(client)
            resp = await client.post(
                f"/api/conversations/{conv_id}/chat/stream",
                json={"content": "Hello"},
            )
        events = _parse_sse(resp.text)
        assert events
        ids = [event_id for event_id, _data in events]
        assert all(isinstance(i, int) for i in ids)
        # Monotonically increasing, contiguous ids starting at 1.
        assert ids == list(range(1, len(ids) + 1))

    @pytest.mark.asyncio
    async def test_last_event_id_resume(
        self, id_env: IdEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Last-Event-ID resumes id numbering past the given value."""
        _patch_agents(monkeypatch)
        async with id_env.anon_client() as client:
            conv_id = await self._create_conv(client)
            resp = await client.post(
                f"/api/conversations/{conv_id}/chat/stream",
                json={"content": "Hello"},
                headers={"Last-Event-ID": "10"},
            )
        events = _parse_sse(resp.text)
        ids = [event_id for event_id, _data in events]
        assert ids[0] == 11
        assert ids == list(range(11, 11 + len(ids)))

    @pytest.mark.asyncio
    async def test_empty_message_emits_error_event(self, id_env: IdEnv) -> None:
        """Scenario: empty content yields a single SSE ``error`` event."""
        async with id_env.anon_client() as client:
            conv_id = await self._create_conv(client)
            resp = await client.post(
                f"/api/conversations/{conv_id}/chat/stream",
                json={"content": "   "},
            )
        assert resp.status_code == 200
        events = _parse_sse(resp.text)
        assert _event_types(events) == ["error"]

    @pytest.mark.asyncio
    async def test_missing_conversation_emits_error_event(
        self, id_env: IdEnv, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: unknown conversation yields an SSE ``error`` event."""
        _patch_agents(monkeypatch)
        async with id_env.anon_client() as client:
            resp = await client.post(
                f"/api/conversations/{NONEXISTENT_UUID}/chat/stream",
                json={"content": "Hello"},
            )
        assert resp.status_code == 200
        events = _parse_sse(resp.text)
        assert _event_types(events) == ["error"]
        assert "not found" in str(events[0][1].get("content", "")).lower()


# ==============================================================================
# Golden snapshots — deterministic byte-identical baselines (AE-0099/0101/0102)
# ==============================================================================
class TestIdentitySnapshots:
    """Auth + admin golden snapshots (body + cookies + JWT shape)."""

    async def _check(self, name: str, resp: Response, *, update: bool) -> None:
        if update:
            id_snapshot.write_snapshot(name, resp)
            return
        id_snapshot.assert_matches_snapshot(name, resp)

    @pytest.mark.asyncio
    async def test_snapshot_login(self, id_env: IdEnv, snapshot_update: bool) -> None:
        """Golden: POST /api/auth/token (200) incl. access_token cookie attrs."""
        async with id_env.anon_client() as client:
            resp = await client.post(
                "/api/auth/token",
                json={"email": ADMIN_EMAIL, "password": LOGIN_PASSWORD},
            )
        await self._check("auth_login", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_login_invalid(
        self, id_env: IdEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /api/auth/token (401)."""
        async with id_env.anon_client() as client:
            resp = await client.post(
                "/api/auth/token",
                json={"email": ADMIN_EMAIL, "password": "wrong"},
            )
        await self._check("auth_login_invalid", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_me(self, id_env: IdEnv, snapshot_update: bool) -> None:
        """Golden: GET /api/auth/me (200)."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.get("/api/auth/me")
        await self._check("auth_me", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_me_unauthenticated(
        self, id_env: IdEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /api/auth/me (401)."""
        async with id_env.anon_client() as client:
            resp = await client.get("/api/auth/me")
        await self._check("auth_me_unauthenticated", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_logout(self, id_env: IdEnv, snapshot_update: bool) -> None:
        """Golden: POST /api/auth/logout (204) incl. cleared cookie attrs."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.post("/api/auth/logout")
        await self._check("auth_logout", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_admin_list_users(
        self, id_env: IdEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /api/admin/users (200)."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.get("/api/admin/users")
        await self._check("admin_list_users", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_admin_list_forbidden(
        self, id_env: IdEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /api/admin/users (403 non-admin)."""
        async with id_env.client_for(id_env.editor) as client:
            resp = await client.get("/api/admin/users")
        await self._check("admin_list_forbidden", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_admin_create_user(
        self, id_env: IdEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /api/admin/users (201)."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.post(
                "/api/admin/users",
                json={
                    "email": "snap-create@integration.example.com",
                    "full_name": "Snap Create",
                    "role": "editor",
                },
            )
        await self._check("admin_create_user", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_admin_create_invalid_role(
        self, id_env: IdEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /api/admin/users (422 invalid role)."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.post(
                "/api/admin/users",
                json={
                    "email": "snap-bad@integration.example.com",
                    "full_name": "Snap Bad",
                    "role": "wizard",
                },
            )
        await self._check("admin_create_invalid_role", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_admin_update_not_found(
        self, id_env: IdEnv, snapshot_update: bool
    ) -> None:
        """Golden: PATCH /api/admin/users/{id} (404)."""
        async with id_env.client_for(id_env.admin) as client:
            resp = await client.patch(
                f"/api/admin/users/{NONEXISTENT_UUID}", json={"role": "editor"}
            )
        await self._check("admin_update_not_found", resp, update=snapshot_update)


class TestConversationSnapshots:
    """Conversation golden snapshots (body + anon cookie + agent header)."""

    async def _check(self, name: str, resp: Response, *, update: bool) -> None:
        if update:
            conv_snapshot.write_snapshot(name, resp)
            return
        conv_snapshot.assert_matches_snapshot(name, resp)

    @pytest.mark.asyncio
    async def test_snapshot_create_authenticated(
        self, id_env: IdEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /api/conversations (201 authenticated, no cookie)."""
        async with id_env.client_for(id_env.editor) as client:
            resp = await client.post("/api/conversations", json={"title": "Snap conv"})
        await self._check("conversation_create", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_create_anonymous(
        self, id_env: IdEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /api/conversations (201 anon) incl. anon_token cookie."""
        async with id_env.anon_client() as client:
            resp = await client.post("/api/conversations", json={"title": "Anon snap"})
        await self._check("conversation_create_anonymous", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_get_not_found(
        self, id_env: IdEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /api/conversations/{id} (404)."""
        async with id_env.client_for(id_env.editor) as client:
            resp = await client.get(f"/api/conversations/{NONEXISTENT_UUID}")
        await self._check("conversation_get_not_found", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_list_empty(
        self, id_env: IdEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /api/conversations (200 empty)."""
        async with id_env.client_for(id_env.editor) as client:
            resp = await client.get("/api/conversations")
        await self._check("conversation_list_empty", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_chat_agent_origin(
        self,
        id_env: IdEnv,
        snapshot_update: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Golden: POST /api/conversations/{id}/chat (200) incl. X-Agent-Origin."""
        _patch_agents(monkeypatch)
        async with id_env.client_for(id_env.editor) as client:
            created = await client.post(
                "/api/conversations", json={"title": "Snap chat"}
            )
            conv_id = created.json()["id"]
            resp = await client.post(
                f"/api/conversations/{conv_id}/chat", json={"content": "Hi"}
            )
        await self._check("conversation_chat", resp, update=snapshot_update)
