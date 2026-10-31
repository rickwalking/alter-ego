"""API tests for renaming a user through ``PATCH /api/admin/users/{id}``.

Scenarios: ``tests/features/admin_edit_user_name_ae0528.feature``. Runs the real
app over a file-backed SQLite database (so the request session and the seeding
session see the same rows) with an admin and an editor already stored.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from rag_backend.domain.models import User, UserRole
from tests.integration.conftest import auth_headers_for, create_test_user

_ADMIN_EMAIL = "rename-admin@integration.example.com"
_EDITOR_EMAIL = "rename-editor@integration.example.com"
_TARGET_EMAIL = "fixed@integration.example.com"
_OTHER_EMAIL = "other@integration.example.com"
_UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"
_NEW_NAME = "John Smith"
_TOO_LONG = "x" * 256


@dataclass(frozen=True)
class _RenameEnv:
    """The app plus the seeded admin, editor and target user."""

    app: FastAPI
    admin: User
    editor: User
    target: User


@pytest_asyncio.fixture
async def rename_env(tmp_path: Path) -> AsyncGenerator[_RenameEnv, None]:
    """A file-backed SQLite app with an admin, an editor and a target user."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.api.middleware.rate_limiting import limiter
    from rag_backend.infrastructure.database.config import Base, close_db

    limiter.reset()
    url = f"sqlite+aiosqlite:///{tmp_path / 'rename.db'}"
    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    env = _RenameEnv(
        app=create_app(),
        admin=await create_test_user(_ADMIN_EMAIL, UserRole.ADMIN),
        editor=await create_test_user(_EDITOR_EMAIL, UserRole.EDITOR),
        target=await create_test_user(_TARGET_EMAIL, UserRole.EDITOR),
    )
    try:
        yield env
    finally:
        db_config.c_engine = None
        await close_db()
        await engine.dispose()


@dataclass(frozen=True)
class _Patch:
    """One ``PATCH /api/admin/users/{target}`` call made by ``actor``."""

    actor: User
    target: str
    body: dict[str, str]


async def _send(env: _RenameEnv, call: _Patch) -> Response:
    """Send ``call`` to the app with the actor's bearer token."""
    transport = ASGITransport(app=env.app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=auth_headers_for(call.actor),
    ) as client:
        return await client.patch(f"/api/admin/users/{call.target}", json=call.body)


async def _stored(user_id: UUID) -> User:
    """The user as stored in the database right now."""
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    async with get_session_maker()() as session:
        user = await PostgresUserRepository(session).get_by_id(user_id)
    assert user is not None
    return user


@pytest.mark.integration
class TestAdminRenameUserApi:
    """The rename path of ``PATCH /api/admin/users/{id}``."""

    # Scenario: Admin renames a user
    async def test_admin_renames_a_user_with_the_name_trimmed(
        self, rename_env: _RenameEnv
    ) -> None:
        target = rename_env.target
        resp = await _send(
            rename_env,
            _Patch(rename_env.admin, str(target.id), {"full_name": "  John Smith  "}),
        )

        assert resp.status_code == 200
        assert resp.json()["full_name"] == _NEW_NAME
        assert (await _stored(target.id)).full_name == _NEW_NAME

    # Scenario: A blank name is rejected
    async def test_a_blank_name_is_rejected(self, rename_env: _RenameEnv) -> None:
        target = rename_env.target
        resp = await _send(
            rename_env, _Patch(rename_env.admin, str(target.id), {"full_name": "   "})
        )

        assert resp.status_code == 422
        assert (await _stored(target.id)).full_name == target.full_name

    # Scenario: A name longer than 255 characters is rejected
    async def test_a_name_over_255_characters_is_rejected(
        self, rename_env: _RenameEnv
    ) -> None:
        target = rename_env.target
        resp = await _send(
            rename_env,
            _Patch(rename_env.admin, str(target.id), {"full_name": _TOO_LONG}),
        )

        assert resp.status_code == 422
        assert (await _stored(target.id)).full_name == target.full_name

    # Scenario: A name longer than 255 characters is rejected
    async def test_a_name_of_exactly_255_characters_is_accepted(
        self, rename_env: _RenameEnv
    ) -> None:
        target = rename_env.target
        resp = await _send(
            rename_env,
            _Patch(rename_env.admin, str(target.id), {"full_name": "y" * 255}),
        )

        assert resp.status_code == 200
        assert resp.json()["full_name"] == "y" * 255

    # Scenario: Omitting the name leaves it unchanged
    async def test_omitting_the_name_leaves_it_unchanged(
        self, rename_env: _RenameEnv
    ) -> None:
        target = rename_env.target
        resp = await _send(
            rename_env, _Patch(rename_env.admin, str(target.id), {"role": "admin"})
        )

        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"
        assert resp.json()["full_name"] == target.full_name

    # Scenario: The email cannot be changed
    async def test_a_sent_email_is_ignored(self, rename_env: _RenameEnv) -> None:
        target = rename_env.target
        body = {"full_name": _NEW_NAME, "email": _OTHER_EMAIL}
        resp = await _send(rename_env, _Patch(rename_env.admin, str(target.id), body))

        assert resp.status_code == 200
        assert resp.json()["email"] == _TARGET_EMAIL
        assert (await _stored(target.id)).email == _TARGET_EMAIL

    # Scenario: A non-admin cannot rename a user
    async def test_a_non_admin_gets_403(self, rename_env: _RenameEnv) -> None:
        target = rename_env.target
        resp = await _send(
            rename_env,
            _Patch(rename_env.editor, str(target.id), {"full_name": "Hacker"}),
        )

        assert resp.status_code == 403
        assert (await _stored(target.id)).full_name == target.full_name

    # Scenario: Renaming an unknown user returns 404
    async def test_an_unknown_user_gets_404(self, rename_env: _RenameEnv) -> None:
        resp = await _send(
            rename_env, _Patch(rename_env.admin, _UNKNOWN_ID, {"full_name": "Nobody"})
        )

        assert resp.status_code == 404

    # Scenario: The last-admin rule still holds when the name is edited with the role
    async def test_last_admin_cannot_self_demote_while_renaming(
        self, rename_env: _RenameEnv
    ) -> None:
        admin = rename_env.admin
        body = {"full_name": "Renamed", "role": "editor"}
        resp = await _send(rename_env, _Patch(admin, str(admin.id), body))

        assert resp.status_code == 409
        stored = await _stored(admin.id)
        assert stored.full_name == admin.full_name
        assert stored.role == UserRole.ADMIN
