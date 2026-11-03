"""An admin password reset logs out the user's open sessions, through the real app.

Scenarios: ``tests/features/admin_reset_logs_out_ae0595.feature``. Runs the
real app over a file-backed SQLite database. Every session holds the bearer
token its own login returned, issued before the reset.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.domain.models import User, UserRole
from tests.integration.change_password_support import (
    CHANGE_URL,
    CODE_CHANGE_REQUIRED,
    CONVERSATIONS_URL,
    ME_URL,
    NEW_PASSWORD,
    OLD_PASSWORD,
    FlowEnv,
    app_over,
    bearer,
    change_body,
    login,
    reset_by_admin,
    seed_user,
    stored_user,
)

_ADMIN_EMAIL = "reset-admin@integration.example.com"
_EDITOR_EMAIL = "reset-editor@integration.example.com"
_OTHER_EMAIL = "reset-other@integration.example.com"
_ADMIN_USERS_URL = "/api/admin/users"
_STALE_DETAIL = "Invalid or expired token"

pytestmark = pytest.mark.integration


@dataclass(frozen=True)
class _Cast:
    """The app, an admin and an editor over a fresh database."""

    env: FlowEnv
    admin: User
    editor: User


@asynccontextmanager
async def _cast(tmp_path: Path) -> AsyncIterator[_Cast]:
    """The app over a fresh SQLite file, with an admin and an editor."""
    from rag_backend.infrastructure.database.config import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'reset.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with app_over(engine) as env:
            admin = await seed_user(_ADMIN_EMAIL, UserRole.ADMIN)
            editor = await seed_user(_EDITOR_EMAIL, UserRole.EDITOR)
            yield _Cast(env=env, admin=admin, editor=editor)
    finally:
        await engine.dispose()


def _reset_url(user_id: UUID) -> str:
    return f"{_ADMIN_USERS_URL}/{user_id}/reset-password"


async def _stale_statuses(client: AsyncClient) -> tuple[int, int, int]:
    """Status of me, change-password and a protected endpoint."""
    me = await client.get(ME_URL)
    changed = await client.post(
        CHANGE_URL, json=change_body(OLD_PASSWORD, NEW_PASSWORD)
    )
    protected = await client.get(CONVERSATIONS_URL)
    return me.status_code, changed.status_code, protected.status_code


# Scenario: An admin reset logs out every open session of the user
async def test_a_reset_logs_out_the_open_session_of_the_user(tmp_path: Path) -> None:
    async with _cast(tmp_path) as cast:
        session = await login(cast.env, (_EDITOR_EMAIL, OLD_PASSWORD))
        async with cast.env.client(bearer(session)) as client:
            before = await client.get(ME_URL)
            await reset_by_admin(cast.env, cast.admin, cast.editor)
            me = await client.get(ME_URL)
            after = await _stale_statuses(client)

        assert before.status_code == 200
        assert me.json() == {"detail": _STALE_DETAIL}
        assert me.headers["www-authenticate"] == "Bearer"
        assert after == (401, 401, 401)
        assert (await stored_user(cast.editor.id)).token_version == 1


# Scenario: The temporary password signs in and must be changed
async def test_the_temporary_password_signs_in_and_must_change(tmp_path: Path) -> None:
    async with _cast(tmp_path) as cast:
        temp_password = await reset_by_admin(cast.env, cast.admin, cast.editor)
        signed_in = await login(cast.env, (_EDITOR_EMAIL, temp_password))
        async with cast.env.client(bearer(signed_in)) as client:
            me = await client.get(ME_URL)
            refused = await client.get(CONVERSATIONS_URL)
            changed = await client.post(
                CHANGE_URL, json=change_body(temp_password, NEW_PASSWORD)
            )

        assert signed_in.status_code == 200
        assert me.json()["must_change_password"] is True
        assert refused.status_code == 403
        assert refused.json()["code"] == CODE_CHANGE_REQUIRED
        assert changed.status_code == 204
        assert (await stored_user(cast.editor.id)).token_version == 2


# Scenario: The admin's session survives the reset of another user
async def test_the_admin_session_survives_the_reset(tmp_path: Path) -> None:
    async with _cast(tmp_path) as cast:
        session = await login(cast.env, (_ADMIN_EMAIL, OLD_PASSWORD))
        async with cast.env.client(bearer(session)) as client:
            reset = await client.post(_reset_url(cast.editor.id))
            me = await client.get(ME_URL)
            listed = await client.get(_ADMIN_USERS_URL)

        assert reset.status_code == 200
        assert (me.status_code, listed.status_code) == (200, 200)
        assert (await stored_user(cast.admin.id)).token_version == 0


# Scenario: An admin who resets their own password is logged out too
async def test_an_admin_resetting_themselves_is_logged_out(tmp_path: Path) -> None:
    async with _cast(tmp_path) as cast:
        session = await login(cast.env, (_ADMIN_EMAIL, OLD_PASSWORD))
        async with cast.env.client(bearer(session)) as client:
            reset = await client.post(_reset_url(cast.admin.id))
            me = await client.get(ME_URL)
        again = await login(cast.env, (_ADMIN_EMAIL, reset.json()["temp_password"]))

        assert reset.status_code == 200
        assert me.status_code == 401
        assert again.status_code == 200
        assert (await stored_user(cast.admin.id)).token_version == 1


# Scenario: A reset of an unknown user changes no token version
async def test_a_reset_of_an_unknown_user_changes_no_version(tmp_path: Path) -> None:
    async with _cast(tmp_path) as cast:
        async with cast.env.client_for(cast.admin) as client:
            missing = await client.post(_reset_url(uuid4()))

        assert missing.status_code == 404
        assert (await stored_user(cast.admin.id)).token_version == 0
        assert (await stored_user(cast.editor.id)).token_version == 0


# Scenario: A reset by a user who is not an admin changes no token version
async def test_a_reset_by_an_editor_changes_no_version(tmp_path: Path) -> None:
    async with _cast(tmp_path) as cast:
        other = await seed_user(_OTHER_EMAIL, UserRole.EDITOR)
        other_session = await login(cast.env, (_OTHER_EMAIL, OLD_PASSWORD))
        async with cast.env.client_for(cast.editor) as client:
            refused = await client.post(_reset_url(other.id))
        async with cast.env.client(bearer(other_session)) as client:
            still_in = await client.get(CONVERSATIONS_URL)

        assert refused.status_code == 403
        assert (await stored_user(other.id)).token_version == 0
        assert (await stored_user(other.id)).must_change_password is False
        assert still_in.status_code == 200
