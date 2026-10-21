"""HTTP behavior for the autopilot service API key.

Gherkin: tests/features/autopilot_api_key.feature
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from structlog.testing import capture_logs

from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.modules.autopilot.api import auth as auth_module
from rag_backend.modules.autopilot.api.auth import require_autopilot_api_key
from rag_backend.modules.autopilot.constants import (
    APP_STATE_SIGNALS,
    DETAIL_API_KEY_INVALID,
    DETAIL_API_KEY_UNCONFIGURED,
    HEADER_API_KEY,
    LOG_API_KEY_DISABLED,
    LOG_API_KEY_REJECTED,
    REASON_KEY_MISMATCH,
    REASON_KEY_MISSING,
)
from rag_backend.modules.autopilot.domain.signals import SignalsBundle

_PLAINTEXT_KEY = "k1"
_WRONG_KEY = "nope"
_SIGNALS_PATH = "/api/autopilot/signals"
_DOCUMENTS_PATH = "/api/documents"
_CAROUSELS_PATH = "/api/carousels"
_AUTOPILOT_PREFIX = "/api/autopilot"
_RATE_LIMIT_BUDGET = 10
_ENV_KEY = "GROKBOT_API_KEY_SHA256"


def _digest(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode(ENCODING_UTF8)).hexdigest()


@pytest.fixture
def configured_key() -> Iterator[str]:
    """Point settings at the sha256 of the scout key, then restore the env."""
    from rag_backend.infrastructure.config.settings import get_settings

    previous = os.environ.get(_ENV_KEY)
    os.environ[_ENV_KEY] = _digest(_PLAINTEXT_KEY)
    get_settings.cache_clear()
    yield _PLAINTEXT_KEY
    if previous is None:
        os.environ.pop(_ENV_KEY, None)
    else:
        os.environ[_ENV_KEY] = previous
    get_settings.cache_clear()


@pytest.fixture
def disabled_key() -> Iterator[None]:
    """Force the autopilot key setting empty even if a developer .env has one."""
    from rag_backend.infrastructure.config.settings import get_settings

    previous = os.environ.get(_ENV_KEY)
    os.environ[_ENV_KEY] = ""
    get_settings.cache_clear()
    yield
    if previous is None:
        os.environ.pop(_ENV_KEY, None)
    else:
        os.environ[_ENV_KEY] = previous
    get_settings.cache_clear()


@pytest.fixture
async def scout(configured_key: str) -> AsyncIterator[AsyncClient]:
    """App client with no user JWT. ``configured_key`` keeps the setting live."""
    del configured_key
    async for client in _open_client():
        yield client


@pytest.fixture
async def scout_disabled(disabled_key: None) -> AsyncIterator[AsyncClient]:
    """App client while the autopilot key setting is empty."""
    del disabled_key
    async for client in _open_client():
        yield client


async def _open_client() -> AsyncIterator[AsyncClient]:
    """Auth tests must not collect live signals, so the signals bundle is replaced by an
    idle fake.
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.api.middleware.rate_limiting import limiter
    from rag_backend.infrastructure.database.config import Base, close_db

    limiter.reset()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    app = create_app()
    setattr(app.state, APP_STATE_SIGNALS, _IdleSignals())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    limiter.reset()
    db_config.c_engine = None
    await close_db()
    await engine.dispose()


def _key_header(value: str) -> dict[str, str]:
    return {HEADER_API_KEY: value}


def _logs_omit_secrets(logs: list[dict[str, object]], *secrets: str) -> None:
    dumped = json.dumps(logs)
    for secret in secrets:
        assert secret not in dumped


# Scenario: Valid key accesses autopilot routes
@pytest.mark.asyncio
async def test_valid_key_returns_200(scout: AsyncClient) -> None:
    response = await scout.get(_SIGNALS_PATH, headers=_key_header(_PLAINTEXT_KEY))
    assert response.status_code == 200
    body = response.json()
    assert body["signals"] == []
    assert body["errors"] == []
    assert isinstance(body["generated_at"], str)


# Scenario: Wrong key is rejected
@pytest.mark.asyncio
async def test_wrong_key_is_401_and_is_not_logged(scout: AsyncClient) -> None:
    with capture_logs() as logs:
        response = await scout.get(_SIGNALS_PATH, headers=_key_header(_WRONG_KEY))
    assert response.status_code == 401
    assert response.json()["detail"] == DETAIL_API_KEY_INVALID
    assert _WRONG_KEY not in response.text
    rejected = [entry for entry in logs if entry.get("event") == LOG_API_KEY_REJECTED]
    assert rejected
    assert rejected[0].get("reason") == REASON_KEY_MISMATCH
    _logs_omit_secrets(logs, _WRONG_KEY, _PLAINTEXT_KEY, _digest(_PLAINTEXT_KEY))


# Scenario: Missing key is rejected
@pytest.mark.asyncio
async def test_missing_key_is_401_and_is_not_logged(scout: AsyncClient) -> None:
    with capture_logs() as logs:
        response = await scout.get(_SIGNALS_PATH)
    assert response.status_code == 401
    assert response.json()["detail"] == DETAIL_API_KEY_INVALID
    rejected = [entry for entry in logs if entry.get("event") == LOG_API_KEY_REJECTED]
    assert rejected
    assert rejected[0].get("reason") == REASON_KEY_MISSING
    _logs_omit_secrets(logs, _PLAINTEXT_KEY, _digest(_PLAINTEXT_KEY))


@pytest.mark.asyncio
async def test_empty_header_is_rejected(scout: AsyncClient) -> None:
    """An empty X-Api-Key is treated as missing, not hashed."""
    response = await scout.get(_SIGNALS_PATH, headers=_key_header(""))
    assert response.status_code == 401


# Scenario: Key does not unlock other routes
@pytest.mark.asyncio
async def test_key_does_not_unlock_user_routes(scout: AsyncClient) -> None:
    documents = await scout.get(_DOCUMENTS_PATH, headers=_key_header(_PLAINTEXT_KEY))
    carousel = await scout.get(
        f"{_CAROUSELS_PATH}/{uuid4()}",
        headers=_key_header(_PLAINTEXT_KEY),
    )
    assert documents.status_code == 401
    assert carousel.status_code == 401


# Scenario: API key is ignored on the public carousel list
@pytest.mark.asyncio
async def test_public_carousel_list_ignores_api_key(scout: AsyncClient) -> None:
    with_key = await scout.get(_CAROUSELS_PATH, headers=_key_header(_PLAINTEXT_KEY))
    without_key = await scout.get(_CAROUSELS_PATH)
    assert with_key.status_code == without_key.status_code
    assert with_key.status_code == 200


# Scenario: Feature disabled
@pytest.mark.asyncio
async def test_unset_key_returns_503(scout_disabled: AsyncClient) -> None:
    with capture_logs() as logs:
        response = await scout_disabled.get(
            _SIGNALS_PATH,
            headers=_key_header(_PLAINTEXT_KEY),
        )
    assert response.status_code == 503
    assert response.json()["detail"] == DETAIL_API_KEY_UNCONFIGURED
    assert _PLAINTEXT_KEY not in response.text
    disabled = [entry for entry in logs if entry.get("event") == LOG_API_KEY_DISABLED]
    assert disabled
    _logs_omit_secrets(logs, _PLAINTEXT_KEY)


@pytest.mark.asyncio
async def test_whitespace_and_uppercase_digest_still_matches(
    scout: AsyncClient,
) -> None:
    """Operators may paste the digest with spaces or uppercase hex."""
    from rag_backend.infrastructure.config.settings import get_settings

    os.environ[_ENV_KEY] = f"  {_digest(_PLAINTEXT_KEY).upper()}  "
    get_settings.cache_clear()
    response = await scout.get(_SIGNALS_PATH, headers=_key_header(_PLAINTEXT_KEY))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_malformed_digest_is_a_mismatch_not_a_crash(
    scout: AsyncClient,
) -> None:
    from rag_backend.infrastructure.config.settings import get_settings

    os.environ[_ENV_KEY] = "not-a-digest"
    get_settings.cache_clear()
    response = await scout.get(_SIGNALS_PATH, headers=_key_header(_PLAINTEXT_KEY))
    assert response.status_code == 401


# Scenario: Autopilot routes share a per-IP rate limit
@pytest.mark.asyncio
async def test_eleventh_request_is_rate_limited(scout: AsyncClient) -> None:
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()
    headers = _key_header(_PLAINTEXT_KEY)
    statuses = [
        (await scout.get(_SIGNALS_PATH, headers=headers)).status_code
        for _ in range(_RATE_LIMIT_BUDGET)
    ]
    blocked = await scout.get(_SIGNALS_PATH, headers=headers)
    assert statuses == [200] * _RATE_LIMIT_BUDGET
    assert blocked.status_code == 429


# Scenario: The API key dependency is only on autopilot routes
def test_api_key_dependency_is_only_on_autopilot_routes() -> None:
    from rag_backend.api.app import create_app

    app = create_app()
    routes = [route for route in app.routes if isinstance(route, APIRoute)]
    autopilot = [route for route in routes if route.path.startswith(_AUTOPILOT_PREFIX)]
    others = [route for route in routes if not route.path.startswith(_AUTOPILOT_PREFIX)]
    assert autopilot
    for route in autopilot:
        assert require_autopilot_api_key in _dependency_calls(route)
    for route in others:
        assert require_autopilot_api_key not in _dependency_calls(route)


def test_compare_digest_receives_hex_not_the_plaintext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Constant-time compare runs on the digests, never the raw key."""
    seen: list[tuple[str, str]] = []
    real = hmac.compare_digest

    def _spy(left: str, right: str) -> bool:
        seen.append((left, right))
        return bool(real(left, right))

    monkeypatch.setattr(auth_module.hmac, "compare_digest", _spy)
    assert auth_module._digests_match(_PLAINTEXT_KEY, _digest(_PLAINTEXT_KEY))
    assert seen == [(_digest(_PLAINTEXT_KEY), _digest(_PLAINTEXT_KEY))]
    assert _PLAINTEXT_KEY not in seen[0][0]
    assert _PLAINTEXT_KEY not in seen[0][1]


class _IdleSignals:
    """Stand-in bundle so API-key tests never open a socket."""

    async def collect_all(self) -> SignalsBundle:
        return SignalsBundle(
            generated_at=datetime(2026, 10, 13, tzinfo=UTC),
            signals=[],
            errors=[],
        )


def _dependency_calls(route: APIRoute) -> list[object]:
    found: list[object] = []

    def _walk(dependant: object) -> None:
        dependencies = getattr(dependant, "dependencies", [])
        for dep in dependencies:
            call = getattr(dep, "call", None)
            if call is not None:
                found.append(call)
            _walk(dep)

    _walk(route.dependant)
    return found
