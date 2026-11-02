"""A password change logs out every other session, through the real app.

Scenarios: ``tests/features/logout_other_sessions_ae0593.feature``. Runs the
real app over a file-backed SQLite database. Session one signs in like the
browser (the session cookie in the client's jar); session two holds the bearer
token its own login returned.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie
from pathlib import Path

import jwt
import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_AUTH
from rag_backend.domain.models import User, UserRole
from rag_backend.infrastructure.config.settings import get_settings
from tests.integration.change_password_support import (
    CHANGE_URL,
    CONVERSATIONS_URL,
    ME_URL,
    NEW_PASSWORD,
    OLD_PASSWORD,
    FlowEnv,
    app_over,
    bearer,
    change_body,
    login,
    seed_user,
    sign_in,
    stored_user,
)

EDITOR_EMAIL = "tv-editor@integration.example.com"
EDITOR_ONLY_URL = "/api/personas"
COOKIE_ACCESS = "access_token"
COOKIE_ANON = "anon_token"
STALE_DETAIL = "Invalid or expired token"

pytestmark = pytest.mark.integration


@asynccontextmanager
async def _env(tmp_path: Path) -> AsyncIterator[tuple[FlowEnv, User]]:
    """The app and an editor over a fresh SQLite file."""
    from rag_backend.infrastructure.database.config import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'tv.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with app_over(engine) as env:
            yield env, await seed_user(EDITOR_EMAIL, UserRole.EDITOR)
    finally:
        await engine.dispose()


def _cookie_attributes(response: Response) -> dict[str, str]:
    """The ``access_token`` Set-Cookie attributes, without its value."""
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    morsel = cookie[COOKIE_ACCESS]
    return {key: str(morsel[key]) for key in morsel if morsel[key] != ""}


def _token_with(user: User, claims: dict[str, object]) -> dict[str, str]:
    """Bearer headers for a hand-made token of ``user`` with extra ``claims``."""
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "type": JWT_TYPE_AUTH,
        "exp": datetime.now(UTC) + timedelta(hours=1),
        **claims,
    }
    secret = get_settings().secret_key.get_secret_value()
    token = jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


async def _statuses(client: AsyncClient) -> tuple[int, int, int]:
    """Status of me, a protected endpoint and an editor-only endpoint."""
    me = await client.get(ME_URL)
    protected = await client.get(CONVERSATIONS_URL)
    editor_only = await client.get(EDITOR_ONLY_URL)
    return me.status_code, protected.status_code, editor_only.status_code


# Scenario: The session that changed the password stays signed in
async def test_the_changing_session_gets_a_fresh_cookie_and_stays_in(
    tmp_path: Path,
) -> None:
    async with _env(tmp_path) as (env, editor), env.client() as first:
        signed_in = await sign_in(first, (EDITOR_EMAIL, OLD_PASSWORD))
        changed = await first.post(
            CHANGE_URL, json=change_body(OLD_PASSWORD, NEW_PASSWORD)
        )
        after = await _statuses(first)

        assert changed.status_code == 204
        assert changed.cookies[COOKIE_ACCESS] != signed_in.cookies[COOKIE_ACCESS]
        assert _cookie_attributes(changed) == _cookie_attributes(signed_in)
        assert after == (200, 200, 200)
        assert (await stored_user(editor.id)).token_version == 1


# Scenario: Every other session is logged out by a password change
async def test_every_other_session_is_logged_out(tmp_path: Path) -> None:
    async with _env(tmp_path) as (env, _editor):
        second_login = await login(env, (EDITOR_EMAIL, OLD_PASSWORD))
        async with env.client(bearer(second_login)) as second:
            before = await _statuses(second)
            async with env.client() as first:
                await sign_in(first, (EDITOR_EMAIL, OLD_PASSWORD))
                await first.post(
                    CHANGE_URL, json=change_body(OLD_PASSWORD, NEW_PASSWORD)
                )
            me = await second.get(ME_URL)
            after = await _statuses(second)
            visitor = await second.post(CONVERSATIONS_URL, json={"title": "Stale"})

        assert before == (200, 200, 200)
        assert me.json() == {"detail": STALE_DETAIL}
        assert me.headers["www-authenticate"] == "Bearer"
        assert after == (401, 401, 401)
        assert visitor.status_code == 201
        assert COOKIE_ANON in visitor.headers["set-cookie"]


# Scenario: A wrong current password does not log anyone out
async def test_a_wrong_current_password_logs_nobody_out(tmp_path: Path) -> None:
    async with _env(tmp_path) as (env, editor):
        second_login = await login(env, (EDITOR_EMAIL, OLD_PASSWORD))
        async with env.client() as first, env.client(bearer(second_login)) as second:
            await sign_in(first, (EDITOR_EMAIL, OLD_PASSWORD))
            refused = await first.post(
                CHANGE_URL, json=change_body("not-the-password", NEW_PASSWORD)
            )
            first_after = await _statuses(first)
            second_after = await _statuses(second)

        assert refused.status_code == 401
        assert "set-cookie" not in refused.headers
        assert (await stored_user(editor.id)).token_version == 0
        assert first_after == (200, 200, 200)
        assert second_after == (200, 200, 200)


# Scenario: Reusing the current password does not log anyone out
async def test_reusing_the_current_password_logs_nobody_out(tmp_path: Path) -> None:
    async with _env(tmp_path) as (env, editor), env.client_for(editor) as client:
        refused = await client.post(
            CHANGE_URL, json=change_body(OLD_PASSWORD, OLD_PASSWORD)
        )
        after = await _statuses(client)

        assert refused.status_code == 400
        assert "set-cookie" not in refused.headers
        assert (await stored_user(editor.id)).token_version == 0
        assert after == (200, 200, 200)


# Scenario: A token without a token version still works for a user at version 0
async def test_a_token_without_tv_works_at_version_0(tmp_path: Path) -> None:
    async with _env(tmp_path) as (env, editor):
        async with env.client(_token_with(editor, {})) as client:
            statuses = await _statuses(client)

        assert statuses == (200, 200, 200)


# Scenario: A token without a token version is refused once the user changed the password
async def test_a_token_without_tv_is_refused_after_a_change(tmp_path: Path) -> None:
    async with _env(tmp_path) as (env, editor):
        pre_versioning = _token_with(editor, {})
        async with env.client_for(editor) as client:
            changed = await client.post(
                CHANGE_URL, json=change_body(OLD_PASSWORD, NEW_PASSWORD)
            )
        async with env.client(pre_versioning) as client:
            statuses = await _statuses(client)

        assert changed.status_code == 204
        assert statuses == (401, 401, 401)


# Scenario: A token whose tv is not a whole number is refused
async def test_a_text_tv_is_refused(tmp_path: Path) -> None:
    async with _env(tmp_path) as (env, editor):
        async with env.client(_token_with(editor, {"tv": "0"})) as client:
            statuses = await _statuses(client)

        assert statuses == (401, 401, 401)
