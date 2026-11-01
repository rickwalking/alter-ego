"""Rate limits key on the real client, trusting forwarded addresses from nginx only.

Scenarios: ``tests/features/rate_limit_client_ip_ae0589.feature``. The app is
wrapped in uvicorn's ``ProxyHeadersMiddleware`` with the ``FORWARDED_ALLOW_IPS``
the production compose file gives the backend container, the way uvicorn runs it
with ``--proxy-headers``. The login checks run the real app over a SQLite file.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from uvicorn._types import ASGI3Application
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from rag_backend.api.middleware.rate_limiting import user_or_address_key
from tests.integration.change_password_support import TOKEN_URL, app_over
from tests.unit.scripts_ci.proxy_client_ip_rules import (
    LOOPBACK,
    forwarded_allow_ips,
    load_compose,
    nginx_address,
)

CLIENT_A = "203.0.113.7"
CLIENT_B = "198.51.100.23"
FORGED = "6.6.6.6"
FRONTEND_PEER = "172.18.0.8"
OUTSIDE_PEER = "192.0.2.99"
PEER_PORT = 40000
XFF = "X-Forwarded-For"
LOGIN_RATE = 5
UNAUTHORIZED = 401
TOO_MANY = 429
OK = 200
UNKNOWN_LOGIN = {"email": "nobody@integration.example.com", "password": "WrongPass123!"}

pytestmark = pytest.mark.integration


def _as_container_runs(app: ASGIApp) -> ASGIApp:
    """``app`` behind the proxy-header handling uvicorn applies in the container."""
    uvicorn_app = cast("ASGI3Application", app)
    trusted = forwarded_allow_ips(load_compose())
    return cast("ASGIApp", ProxyHeadersMiddleware(uvicorn_app, trusted_hosts=trusted))


async def _key_probe(scope: Scope, receive: Receive, send: Send) -> None:
    """Answer with the rate-limit key the request resolves to."""
    response = PlainTextResponse(user_or_address_key(Request(scope, receive)))
    await response(scope, receive, send)


def _client(app: ASGIApp, peer: str) -> AsyncClient:
    transport = ASGITransport(app=app, client=(peer, PEER_PORT))
    return AsyncClient(transport=transport, base_url="http://test")


async def _key(peer: str, forwarded_for: str) -> str:
    async with _client(_as_container_runs(_key_probe), peer) as client:
        response = await client.get("/", headers={XFF: forwarded_for})
    return response.text


def test_nginx_has_a_fixed_trusted_address() -> None:
    """The probe below uses the compose file's nginx address, so it must exist."""
    assert nginx_address(load_compose()) != ""


# Scenario: A request through nginx keys the limiter on the forwarded client
async def test_request_through_nginx_keys_on_the_client() -> None:
    """nginx is trusted, so its X-Forwarded-For becomes the client address."""
    assert await _key(nginx_address(load_compose()), CLIENT_A) == CLIENT_A


# Scenario: A forwarded address from an untrusted peer is ignored
@pytest.mark.parametrize("peer", [OUTSIDE_PEER, FRONTEND_PEER])
async def test_untrusted_peer_header_is_ignored(peer: str) -> None:
    """Any peer but nginx (or loopback) keys on its own address."""
    assert await _key(peer, CLIENT_A) == peer


# Scenario: A forged left-most X-Forwarded-For entry is ignored
async def test_forged_left_most_entry_is_ignored() -> None:
    """The right-most untrusted hop wins, not the client-supplied first entry."""
    nginx = nginx_address(load_compose())
    assert await _key(nginx, f"{FORGED}, {CLIENT_A}") == CLIENT_A


@asynccontextmanager
async def _login_app(tmp_path: Path) -> AsyncIterator[ASGIApp]:
    from rag_backend.infrastructure.database.config import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ip.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with app_over(engine) as env:
            yield _as_container_runs(env.app)
    finally:
        await engine.dispose()


async def _login_status(app: ASGIApp, client_ip: str) -> int:
    async with _client(app, nginx_address(load_compose())) as client:
        response = await client.post(
            TOKEN_URL, json=UNKNOWN_LOGIN, headers={XFF: client_ip}
        )
    return response.status_code


# Scenario: Two clients through nginx get separate login buckets
async def test_two_clients_get_separate_login_buckets(tmp_path: Path) -> None:
    """Client A exhausting the login limit leaves client B's bucket untouched."""
    async with _login_app(tmp_path) as app:
        statuses = [await _login_status(app, CLIENT_A) for _ in range(LOGIN_RATE + 1)]
        other = await _login_status(app, CLIENT_B)
    assert statuses == [UNAUTHORIZED] * LOGIN_RATE + [TOO_MANY]
    assert other == UNAUTHORIZED


# Scenario: The container healthcheck keeps working
async def test_loopback_healthcheck_answers(tmp_path: Path) -> None:
    """The HEALTHCHECK curl comes from 127.0.0.1 with no forwarded header."""
    async with _login_app(tmp_path) as app, _client(app, LOOPBACK) as client:
        response = await client.get("/health")
    assert response.status_code == OK
