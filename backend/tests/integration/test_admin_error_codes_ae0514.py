"""API tests for the stable error ``code`` on admin and login errors.

Scenarios: ``tests/features/admin_error_codes_ae0514.feature``. Runs the real
app over a file-backed SQLite database with one admin (the only admin), an
active user and a deactivated user, both with a known password.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from rag_backend.domain.models import User, UserRole
from rag_backend.infrastructure.auth import hash_password
from tests.integration.conftest import auth_headers_for, create_test_user

_ADMIN_EMAIL = "codes-admin@integration.example.com"
_ACTIVE_EMAIL = "codes-active@integration.example.com"
_INACTIVE_EMAIL = "codes-inactive@integration.example.com"
_PASSWORD = "a-known-password-123"
_USERS_URL = "/api/admin/users"
_LOGIN_URL = "/api/auth/token"


@dataclass(frozen=True)
class _CodesEnv:
    """The app plus the seeded admin."""

    app: FastAPI
    admin: User


@dataclass(frozen=True)
class _Call:
    """One HTTP call; ``actor`` signs it with a bearer token when set."""

    method: str
    url: str
    body: dict[str, str] = field(default_factory=dict)
    actor: User | None = None


async def _seed_with_password(email: str, active: bool) -> User:
    """Persist an editor whose bcrypt hash matches ``_PASSWORD``."""
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    async with get_session_maker()() as session:
        user = User(
            email=email,
            full_name="Seeded User",
            role=UserRole.EDITOR,
            hashed_password=hash_password(_PASSWORD),
            is_active=active,
        )
        created = await PostgresUserRepository(session).create(user)
        await session.commit()
    return created


@pytest_asyncio.fixture
async def codes_env(tmp_path: Path) -> AsyncGenerator[_CodesEnv, None]:
    """A file-backed SQLite app with one admin and two password users."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.api.middleware.rate_limiting import limiter
    from rag_backend.infrastructure.database.config import Base, close_db

    limiter.reset()
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'codes.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    env = _CodesEnv(
        app=create_app(), admin=await create_test_user(_ADMIN_EMAIL, UserRole.ADMIN)
    )
    await _seed_with_password(_ACTIVE_EMAIL, active=True)
    await _seed_with_password(_INACTIVE_EMAIL, active=False)
    try:
        yield env
    finally:
        db_config.c_engine = None
        await close_db()
        await engine.dispose()


async def _send(env: _CodesEnv, call: _Call) -> Response:
    """Send ``call`` to the app, signed by its actor when it has one."""
    headers = auth_headers_for(call.actor) if call.actor is not None else {}
    transport = ASGITransport(app=env.app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=headers
    ) as client:
        if call.method == "DELETE":
            return await client.delete(call.url)
        return await client.request(call.method, call.url, json=call.body)


def _login(email: str, password: str) -> _Call:
    """A login call for ``email`` with ``password``."""
    return _Call("POST", _LOGIN_URL, {"email": email, "password": password})


@pytest.mark.integration
class TestAdminErrorCodes:
    """The additive ``code`` field on admin and login error bodies."""

    # Scenario: A duplicate email on create returns the email-exists code
    async def test_duplicate_email_has_the_email_exists_code(
        self, codes_env: _CodesEnv
    ) -> None:
        body = {"email": _ACTIVE_EMAIL, "full_name": "Someone Else"}
        resp = await _send(codes_env, _Call("POST", _USERS_URL, body, codes_env.admin))

        assert resp.status_code == 409
        assert resp.json()["code"] == "user_email_exists"
        assert _ACTIVE_EMAIL in resp.json()["detail"]

    # Scenario: A deactivated account cannot sign in and gets the inactive code
    async def test_deactivated_login_has_the_inactive_code(
        self, codes_env: _CodesEnv
    ) -> None:
        resp = await _send(codes_env, _login(_INACTIVE_EMAIL, _PASSWORD))

        assert resp.status_code == 401
        assert resp.json() == {
            "detail": "User account is deactivated",
            "code": "user_inactive",
        }

    # Scenario: Wrong credentials keep the plain invalid-credentials answer
    async def test_wrong_password_has_no_code(self, codes_env: _CodesEnv) -> None:
        resp = await _send(codes_env, _login(_ACTIVE_EMAIL, "wrong-password-000"))

        assert resp.status_code == 401
        assert resp.json() == {"detail": "Invalid email or password"}

    # Scenario: Deleting your own account returns the self-delete code
    async def test_self_delete_has_the_self_delete_code(
        self, codes_env: _CodesEnv
    ) -> None:
        url = f"{_USERS_URL}/{codes_env.admin.id}"
        resp = await _send(codes_env, _Call("DELETE", url, actor=codes_env.admin))

        assert resp.status_code == 409
        assert resp.json()["code"] == "self_delete"
        assert resp.json()["detail"] == "Cannot delete your own account"

    # Scenario: Demoting the last admin returns the last-admin code
    async def test_demoting_the_last_admin_has_the_last_admin_code(
        self, codes_env: _CodesEnv
    ) -> None:
        url = f"{_USERS_URL}/{codes_env.admin.id}"
        resp = await _send(
            codes_env, _Call("PATCH", url, {"role": "editor"}, codes_env.admin)
        )

        assert resp.status_code == 409
        assert resp.json()["code"] == "last_admin"
        assert resp.json()["detail"] == "Cannot demote the last admin"
