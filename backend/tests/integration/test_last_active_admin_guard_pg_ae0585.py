"""The last-active-admin guard of ``PATCH /api/admin/users/{id}`` on real Postgres.

Scenarios: ``tests/features/last_active_admin_guard_ae0585.feature``. Runs the real
app against a throwaway Postgres schema holding only the ``users`` table, so the
active-admin count is the real SQL ``count`` the production adapter runs. Skipped
unless ``DATABASE_URL`` points at Postgres (CI's backend test job does).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from rag_backend.domain.models import User, UserRole
from tests.integration.conftest import auth_headers_for
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_TABLES = ("users",)
_USERS_URL = "/api/admin/users"
_ME_EMAIL = "guard-me@integration.example.com"
_OTHER_EMAIL = "guard-other@integration.example.com"
_EDITOR_EMAIL = "guard-editor@integration.example.com"
_CODE_LAST_ADMIN = "last_admin"
_DEACTIVATE_DETAIL = "Cannot deactivate the last active admin"
_DEMOTE_DETAIL = "Cannot demote the last admin"
_CONFLICT = 409
_OK = 200

pytestmark = [pytest.mark.integration, requires_postgres]


@dataclass(frozen=True)
class _Seed:
    """One user to persist before the app is called."""

    email: str
    role: UserRole
    is_active: bool = True


@dataclass(frozen=True)
class _GuardEnv:
    """The app over the throwaway schema."""

    app: FastAPI


@asynccontextmanager
async def _guard_env() -> AsyncIterator[_GuardEnv]:
    """The real app whose database is a fresh Postgres schema with ``users``.

    Opened inside each test (not a fixture) so the asyncpg pool lives on the
    test's own event loop.
    """
    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()
    async with isolated_schema(_TABLES) as engine:
        db_config.c_engine = engine
        try:
            yield _GuardEnv(app=create_app())
        finally:
            db_config.c_engine = None


async def _seed(seed: _Seed) -> User:
    """Persist ``seed`` through the production repository and commit."""
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    async with get_session_maker()() as session:
        user = User(
            email=seed.email,
            full_name="Guard User",
            role=seed.role,
            hashed_password="not-used-in-tests",
            is_active=seed.is_active,
        )
        created = await PostgresUserRepository(session).create(user)
        await session.commit()
    return created


async def _stored(user_id: UUID) -> User:
    """Read the user back from Postgres in a fresh session."""
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    async with get_session_maker()() as session:
        user = await PostgresUserRepository(session).get_by_id(user_id)
    assert user is not None
    return user


async def _patch(
    env: _GuardEnv, actor: User, change: tuple[UUID, dict[str, object]]
) -> Response:
    """PATCH ``change`` (target id, body) as ``actor``."""
    target, body = change
    transport = ASGITransport(app=env.app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=auth_headers_for(actor)
    ) as client:
        return await client.patch(f"{_USERS_URL}/{target}", json=body)


class TestLastActiveAdminGuardOnPostgres:
    """The last-active-admin guard through the HTTP API on Postgres."""

    # Scenario: Deactivating the last active admin is refused
    async def test_deactivating_the_last_active_admin_returns_409(self) -> None:
        async with _guard_env() as guard_env:
            me = await _seed(_Seed(_ME_EMAIL, UserRole.ADMIN))

            resp = await _patch(guard_env, me, (me.id, {"is_active": False}))

            assert resp.status_code == _CONFLICT
            assert resp.json() == {
                "detail": _DEACTIVATE_DETAIL,
                "code": _CODE_LAST_ADMIN,
            }
            stored = await _stored(me.id)
            assert stored.is_active is True
            assert stored.role == UserRole.ADMIN

    # Scenario: Demoting is refused when the other admins are inactive
    async def test_demoting_with_an_inactive_other_admin_returns_409(self) -> None:
        async with _guard_env() as guard_env:
            me = await _seed(_Seed(_ME_EMAIL, UserRole.ADMIN))
            await _seed(_Seed(_OTHER_EMAIL, UserRole.ADMIN, is_active=False))

            resp = await _patch(guard_env, me, (me.id, {"role": "editor"}))

            assert resp.status_code == _CONFLICT
            assert resp.json() == {"detail": _DEMOTE_DETAIL, "code": _CODE_LAST_ADMIN}
            assert (await _stored(me.id)).role == UserRole.ADMIN

    # Scenario: Demoting and deactivating in one request is refused as a demotion
    async def test_demote_and_deactivate_together_returns_409(self) -> None:
        async with _guard_env() as guard_env:
            me = await _seed(_Seed(_ME_EMAIL, UserRole.ADMIN))

            resp = await _patch(
                guard_env, me, (me.id, {"role": "editor", "is_active": False})
            )

            assert resp.status_code == _CONFLICT
            assert resp.json()["code"] == _CODE_LAST_ADMIN
            stored = await _stored(me.id)
            assert stored.role == UserRole.ADMIN
            assert stored.is_active is True

    # Scenario: With two active admins one can be deactivated
    async def test_deactivating_with_two_active_admins_is_allowed(self) -> None:
        async with _guard_env() as guard_env:
            me = await _seed(_Seed(_ME_EMAIL, UserRole.ADMIN))
            await _seed(_Seed(_OTHER_EMAIL, UserRole.ADMIN))

            resp = await _patch(guard_env, me, (me.id, {"is_active": False}))

            assert resp.status_code == _OK
            assert resp.json()["is_active"] is False
            assert (await _stored(me.id)).is_active is False

    # Scenario: With two active admins one can be demoted
    async def test_demoting_with_two_active_admins_is_allowed(self) -> None:
        async with _guard_env() as guard_env:
            me = await _seed(_Seed(_ME_EMAIL, UserRole.ADMIN))
            await _seed(_Seed(_OTHER_EMAIL, UserRole.ADMIN))

            resp = await _patch(guard_env, me, (me.id, {"role": "editor"}))

            assert resp.status_code == _OK
            assert resp.json()["role"] == "editor"
            assert (await _stored(me.id)).role == UserRole.EDITOR

    # Scenario: An inactive admin can be demoted while one active admin remains
    async def test_demoting_an_inactive_admin_is_allowed(self) -> None:
        async with _guard_env() as guard_env:
            me = await _seed(_Seed(_ME_EMAIL, UserRole.ADMIN))
            other = await _seed(_Seed(_OTHER_EMAIL, UserRole.ADMIN, is_active=False))

            resp = await _patch(guard_env, me, (other.id, {"role": "editor"}))

            assert resp.status_code == _OK
            assert (await _stored(other.id)).role == UserRole.EDITOR

    # Scenario: Editors and other changes are not affected by the guard
    async def test_deactivating_an_editor_is_allowed(self) -> None:
        async with _guard_env() as guard_env:
            me = await _seed(_Seed(_ME_EMAIL, UserRole.ADMIN))
            editor = await _seed(_Seed(_EDITOR_EMAIL, UserRole.EDITOR))

            resp = await _patch(guard_env, me, (editor.id, {"is_active": False}))

            assert resp.status_code == _OK
            assert (await _stored(editor.id)).is_active is False

    # Scenario: Deactivating is refused when the other admins are inactive
    async def test_deactivating_with_an_inactive_other_admin_returns_409(
        self,
    ) -> None:
        async with _guard_env() as guard_env:
            me = await _seed(_Seed(_ME_EMAIL, UserRole.ADMIN))
            await _seed(_Seed(_OTHER_EMAIL, UserRole.ADMIN, is_active=False))

            resp = await _patch(guard_env, me, (me.id, {"is_active": False}))

            assert resp.status_code == _CONFLICT
            assert resp.json() == {
                "detail": _DEACTIVATE_DETAIL,
                "code": _CODE_LAST_ADMIN,
            }
            assert (await _stored(me.id)).is_active is True
