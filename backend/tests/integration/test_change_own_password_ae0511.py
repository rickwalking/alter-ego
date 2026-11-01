"""Self-service password change and the forced change after an admin reset.

Scenarios: ``tests/features/change_own_password_ae0511.feature``. Runs the real
app over a file-backed SQLite database (overlapping sessions see one database).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.domain.constants import MIN_PASSWORD_LENGTH
from rag_backend.domain.models import User, UserRole
from tests.integration.change_password_support import (
    CHANGE_URL,
    CODE_CHANGE_REQUIRED,
    CONVERSATIONS_URL,
    LOGOUT_URL,
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

ADMIN_EMAIL = "pw-admin@integration.example.com"
EDITOR_EMAIL = "pw-editor@integration.example.com"
LOGIN_RATE = 5
COOKIE_ANON = "anon_token"

pytestmark = pytest.mark.integration


@asynccontextmanager
async def _env(tmp_path: Path) -> AsyncIterator[tuple[FlowEnv, User, User]]:
    """The app, an admin and an editor over a fresh SQLite file."""
    from rag_backend.infrastructure.database.config import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'pw.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with app_over(engine) as env:
            admin = await seed_user(ADMIN_EMAIL, UserRole.ADMIN)
            editor = await seed_user(EDITOR_EMAIL, UserRole.EDITOR)
            yield env, admin, editor
    finally:
        await engine.dispose()


async def _change(env: FlowEnv, user: User, body: dict[str, str]) -> int:
    async with env.client_for(user) as client:
        return (await client.post(CHANGE_URL, json=body)).status_code


# Scenario: A signed-in user changes their own password
async def test_a_user_changes_their_own_password(tmp_path: Path) -> None:
    async with _env(tmp_path) as (env, _admin, editor):
        status = await _change(env, editor, change_body(OLD_PASSWORD, NEW_PASSWORD))

        assert status == 204
        assert (await login(env, (EDITOR_EMAIL, NEW_PASSWORD))).status_code == 200
        assert (await login(env, (EDITOR_EMAIL, OLD_PASSWORD))).status_code == 401
        assert (await stored_user(editor.id)).must_change_password is False


# Scenario: A wrong current password changes nothing
async def test_a_wrong_current_password_changes_nothing(tmp_path: Path) -> None:
    async with _env(tmp_path) as (env, _admin, editor):
        async with env.client_for(editor) as client:
            resp = await client.post(
                CHANGE_URL, json=change_body("not-the-password", NEW_PASSWORD)
            )

        assert resp.status_code == 401
        assert resp.json() == {
            "detail": "Current password is incorrect",
            "code": "current_password_incorrect",
        }
        assert (await login(env, (EDITOR_EMAIL, OLD_PASSWORD))).status_code == 200


# Scenario: A new password equal to the current one is refused
async def test_the_same_password_is_refused(tmp_path: Path) -> None:
    async with _env(tmp_path) as (env, admin, editor):
        temp = await reset_by_admin(env, admin, editor)
        async with env.client_for(editor) as client:
            resp = await client.post(CHANGE_URL, json=change_body(temp, temp))

        assert resp.status_code == 400
        assert resp.json()["code"] == "password_unchanged"
        stored = await stored_user(editor.id)
        assert stored.must_change_password is True
        assert (await login(env, (EDITOR_EMAIL, temp))).status_code == 200


# Scenario: A new password shorter than the policy is refused
async def test_a_short_new_password_is_refused(tmp_path: Path) -> None:
    async with _env(tmp_path) as (env, _admin, editor):
        short = "x" * (MIN_PASSWORD_LENGTH - 1)
        status = await _change(env, editor, change_body(OLD_PASSWORD, short))

        assert status == 422
        assert (await login(env, (EDITOR_EMAIL, OLD_PASSWORD))).status_code == 200


# Scenario: Changing the password is rate limited like the login
async def test_changing_the_password_is_rate_limited(tmp_path: Path) -> None:
    async with _env(tmp_path) as (env, _admin, editor):
        wrong = change_body("not-the-password", NEW_PASSWORD)
        statuses = [await _change(env, editor, wrong) for _ in range(LOGIN_RATE + 1)]

        assert statuses[:LOGIN_RATE] == [401] * LOGIN_RATE
        assert statuses[LOGIN_RATE] == 429


# Scenario: An admin reset makes the user change the password at next login
async def test_an_admin_reset_flags_the_user(tmp_path: Path) -> None:
    async with _env(tmp_path) as (env, admin, editor):
        temp = await reset_by_admin(env, admin, editor)

        assert len(temp) >= MIN_PASSWORD_LENGTH
        assert (await stored_user(editor.id)).must_change_password is True
        assert (await stored_user(admin.id)).must_change_password is False


# Scenario: A user with a temporary password is refused on protected endpoints
async def test_a_flagged_user_is_refused_except_me_and_logout(tmp_path: Path) -> None:
    async with _env(tmp_path) as (env, admin, editor):
        temp = await reset_by_admin(env, admin, editor)
        token = await login(env, (EDITOR_EMAIL, temp))
        assert token.status_code == 200
        async with env.client(bearer(token)) as client:
            me = await client.get(ME_URL)
            refused = await client.get(CONVERSATIONS_URL)
            logout = await client.post(LOGOUT_URL)

        assert me.status_code == 200
        assert me.json()["must_change_password"] is True
        assert refused.status_code == 403
        assert refused.json() == {
            "detail": "Password change required",
            "code": CODE_CHANGE_REQUIRED,
        }
        assert logout.status_code == 204


# Scenario: A user with a temporary password is refused on protected endpoints
async def test_a_flagged_admin_is_refused_on_role_guarded_endpoints(
    tmp_path: Path,
) -> None:
    async with _env(tmp_path) as (env, admin, _editor):
        await reset_by_admin(env, admin, admin)
        async with env.client_for(admin) as client:
            users = await client.get("/api/admin/users")
            rubrics = await client.get("/api/rubrics")

        assert users.status_code == 403
        assert users.json()["code"] == CODE_CHANGE_REQUIRED
        assert rubrics.status_code == 403
        assert rubrics.json()["code"] == CODE_CHANGE_REQUIRED


# Scenario: Changing a temporary password clears the flag
async def test_changing_the_temporary_password_clears_the_flag(
    tmp_path: Path,
) -> None:
    async with _env(tmp_path) as (env, admin, editor):
        temp = await reset_by_admin(env, admin, editor)
        async with env.client_for(editor) as client:
            changed = await client.post(
                CHANGE_URL, json=change_body(temp, NEW_PASSWORD)
            )
            me = await client.get(ME_URL)
            listed = await client.get(CONVERSATIONS_URL)

        assert changed.status_code == 204
        assert me.json()["must_change_password"] is False
        assert listed.status_code == 200
        assert (await login(env, (EDITOR_EMAIL, NEW_PASSWORD))).status_code == 200


# Scenario: A flagged user is treated as anonymous on public endpoints
async def test_a_flagged_user_is_anonymous_on_optional_endpoints(
    tmp_path: Path,
) -> None:
    async with _env(tmp_path) as (env, admin, editor):
        await reset_by_admin(env, admin, editor)
        async with env.client_for(editor) as client:
            resp = await client.post(CONVERSATIONS_URL, json={"title": "As visitor"})

        assert resp.status_code == 201
        assert COOKIE_ANON in resp.headers["set-cookie"]
