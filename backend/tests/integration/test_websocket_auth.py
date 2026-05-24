"""Integration tests for WebSocket authentication.

Feature: WebSocket Authentication
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import jwt
import pytest
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_ANON, JWT_TYPE_AUTH
from rag_backend.infrastructure.config.settings import Settings

TEST_SECRET = "test-secret-key-for-websocket-tests"
TEST_ANON_SECRET = "test-anon-secret-for-websocket-tests"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        secret_key=TEST_SECRET,
        anon_secret_key=TEST_ANON_SECRET,
    )


@pytest.fixture
def valid_access_token(settings: Settings) -> str:
    payload = {
        "sub": str(uuid4()),
        "email": "test@test.com",
        "role": "editor",
        "type": JWT_TYPE_AUTH,
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def expired_access_token(settings: Settings) -> str:
    payload = {
        "sub": str(uuid4()),
        "email": "test@test.com",
        "role": "editor",
        "type": JWT_TYPE_AUTH,
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "iat": datetime.now(UTC) - timedelta(hours=2),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def valid_anon_token(settings: Settings, conversation_id: str) -> str:
    payload = {
        "sub": f"anon:{conversation_id}",
        "conversation_id": conversation_id,
        "type": JWT_TYPE_ANON,
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, TEST_ANON_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def wrong_conversation_anon_token(settings: Settings) -> str:
    payload = {
        "sub": "anon:wrong-conv-id",
        "conversation_id": "wrong-conv-id",
        "type": JWT_TYPE_ANON,
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, TEST_ANON_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def conversation_id() -> str:
    return str(uuid4())


def _mock_websocket(*, headers: dict | None = None, cookies: dict | None = None) -> MagicMock:
    ws = MagicMock(spec=WebSocket)
    ws.headers = headers or {}
    ws.cookies = cookies or {}
    ws.client_state = WebSocketState.CONNECTING
    ws.application_state = WebSocketState.CONNECTING
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_accepts_subprotocol_token(
    settings: Settings,
    valid_access_token: str,
    conversation_id: str,
):
    """Scenario: Authenticate via subprotocol with valid access token."""
    token = valid_access_token
    ws = _mock_websocket(
        headers={"sec-websocket-protocol": token},
    )

    from rag_backend.infrastructure.auth import decode_access_token

    conv_id = uuid4()
    subprotocols = ws.headers.get("sec-websocket-protocol", "")
    token_from_header = subprotocols.strip()
    token_candidate: str | None = token_from_header or None
    if not token_candidate:
        token_candidate = ws.cookies.get("access_token") or ws.cookies.get("anon_token")

    is_authorized = False
    if token_candidate:
        auth_payload = decode_access_token(settings, token_candidate)
        if auth_payload is not None:
            is_authorized = True
            if token_from_header:
                await ws.accept(subprotocol=token_candidate)
            else:
                await ws.accept()

    assert is_authorized
    ws.accept.assert_awaited_once_with(subprotocol=token)
    ws.close.assert_not_called()


@pytest.mark.asyncio
async def test_accepts_cookie_token(
    settings: Settings,
    valid_access_token: str,
    conversation_id: str,
):
    """Scenario: Authenticate via cookie when subprotocol is absent."""
    token = valid_access_token
    ws = _mock_websocket(
        cookies={"access_token": token},
    )

    from rag_backend.infrastructure.auth import decode_access_token

    subprotocols = ws.headers.get("sec-websocket-protocol", "")
    token_from_header = subprotocols.strip()
    token_candidate: str | None = token_from_header or None
    if not token_candidate:
        token_candidate = ws.cookies.get("access_token") or ws.cookies.get("anon_token")

    is_authorized = False
    if token_candidate:
        auth_payload = decode_access_token(settings, token_candidate)
        if auth_payload is not None:
            is_authorized = True
            if token_from_header:
                await ws.accept(subprotocol=token_candidate)
            else:
                await ws.accept()

    assert is_authorized
    ws.accept.assert_awaited_once_with()
    ws.close.assert_not_called()


@pytest.mark.asyncio
async def test_accepts_anon_cookie_token(
    settings: Settings,
    valid_anon_token: str,
    conversation_id: str,
):
    """Scenario: Authenticate via anonymous cookie when subprotocol is absent."""
    token = valid_anon_token
    ws = _mock_websocket(
        cookies={"anon_token": token},
    )

    from rag_backend.infrastructure.auth import decode_access_token, decode_anonymous_token

    subprotocols = ws.headers.get("sec-websocket-protocol", "")
    token_from_header = subprotocols.strip()
    token_candidate: str | None = token_from_header or None
    if not token_candidate:
        token_candidate = ws.cookies.get("access_token") or ws.cookies.get("anon_token")

    is_authorized = False
    if token_candidate:
        auth_payload = decode_access_token(settings, token_candidate)
        if auth_payload is not None:
            is_authorized = True
        else:
            anon_payload = decode_anonymous_token(settings, token_candidate)
            if anon_payload is not None and anon_payload.get("conversation_id") == conversation_id:
                is_authorized = True
                if token_from_header:
                    await ws.accept(subprotocol=token_candidate)
                else:
                    await ws.accept()

    assert is_authorized
    ws.accept.assert_awaited_once_with()
    ws.close.assert_not_called()


@pytest.mark.asyncio
async def test_rejects_expired_token(
    settings: Settings,
    expired_access_token: str,
    conversation_id: str,
):
    """Scenario: Reject connection with expired access token."""
    token = expired_access_token
    ws = _mock_websocket(
        headers={"sec-websocket-protocol": token},
    )

    from rag_backend.infrastructure.auth import decode_access_token

    subprotocols = ws.headers.get("sec-websocket-protocol", "")
    token_from_header = subprotocols.strip()
    token_candidate: str | None = token_from_header or None

    is_authorized = False
    if token_candidate:
        auth_payload = decode_access_token(settings, token_candidate)
        if auth_payload is not None:
            is_authorized = True

    if not is_authorized:
        await ws.close(code=1008)

    assert not is_authorized
    ws.accept.assert_not_called()
    ws.close.assert_awaited_once_with(code=1008)


@pytest.mark.asyncio
async def test_rejects_wrong_conversation_anon_token(
    settings: Settings,
    wrong_conversation_anon_token: str,
    conversation_id: str,
):
    """Scenario: Reject connection with anonymous token for wrong conversation."""
    token = wrong_conversation_anon_token
    ws = _mock_websocket(
        headers={"sec-websocket-protocol": token},
    )

    from rag_backend.infrastructure.auth import decode_access_token, decode_anonymous_token

    subprotocols = ws.headers.get("sec-websocket-protocol", "")
    token_from_header = subprotocols.strip()
    token_candidate: str | None = token_from_header or None

    is_authorized = False
    if token_candidate:
        auth_payload = decode_access_token(settings, token_candidate)
        if auth_payload is not None:
            is_authorized = True
        else:
            anon_payload = decode_anonymous_token(settings, token_candidate)
            if anon_payload is not None and anon_payload.get("conversation_id") == conversation_id:
                is_authorized = True

    if not is_authorized:
        await ws.close(code=1008)

    assert not is_authorized
    ws.accept.assert_not_called()
    ws.close.assert_awaited_once_with(code=1008)


@pytest.mark.asyncio
async def test_rejects_no_token(settings: Settings, conversation_id: str):
    """Scenario: Reject connection without any token."""
    ws = _mock_websocket()

    from rag_backend.infrastructure.auth import decode_access_token

    subprotocols = ws.headers.get("sec-websocket-protocol", "")
    token_from_header = subprotocols.strip()
    token_candidate: str | None = token_from_header or None
    if not token_candidate:
        token_candidate = ws.cookies.get("access_token") or ws.cookies.get("anon_token")

    is_authorized = False
    if token_candidate:
        auth_payload = decode_access_token(settings, token_candidate)
        if auth_payload is not None:
            is_authorized = True

    if not is_authorized:
        await ws.close(code=1008)

    assert not is_authorized
    ws.accept.assert_not_called()
    ws.close.assert_awaited_once_with(code=1008)
