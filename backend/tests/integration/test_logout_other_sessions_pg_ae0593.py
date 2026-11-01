"""Token versions on real Postgres: the logout flow and concurrent changes.

Scenarios: ``tests/features/logout_other_sessions_ae0593.feature``. Runs the
real app against a throwaway Postgres schema holding the users and
conversations tables, so the version is the real column the production adapter
reads and writes, and the row lock a change takes is a real Postgres lock.
Skipped unless ``DATABASE_URL`` points at Postgres (CI's
backend test job does).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models import UserRole
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
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_TABLES = ("users", "conversations", "messages")
_EDITOR_EMAIL = "tv-pg-editor@integration.example.com"
_THIRD_PASSWORD = "ThirdSecurePass789!"
_COOKIE_ACCESS = "access_token"
_LOCK_WAIT_SECONDS = 0.5

pytestmark = [pytest.mark.integration, requires_postgres]


@asynccontextmanager
async def _pg_env() -> AsyncIterator[FlowEnv]:
    """The real app over a fresh Postgres schema (opened inside each test)."""
    async with isolated_schema(_TABLES) as engine, app_over(engine) as env:
        yield env


# Scenario: Every other session is logged out by a password change
async def test_a_change_on_postgres_logs_out_the_other_session_only() -> None:
    async with _pg_env() as env:
        editor = await seed_user(_EDITOR_EMAIL, UserRole.EDITOR)
        other = await login(env, (_EDITOR_EMAIL, OLD_PASSWORD))
        async with env.client() as first, env.client(bearer(other)) as second:
            await sign_in(first, (_EDITOR_EMAIL, OLD_PASSWORD))
            changed = await first.post(
                CHANGE_URL, json=change_body(OLD_PASSWORD, NEW_PASSWORD)
            )
            first_me = await first.get(ME_URL)
            first_list = await first.get(CONVERSATIONS_URL)
            second_me = await second.get(ME_URL)
            second_list = await second.get(CONVERSATIONS_URL)

        assert changed.status_code == 204
        assert (await stored_user(editor.id)).token_version == 1
        assert (first_me.status_code, first_list.status_code) == (200, 200)
        assert (second_me.status_code, second_list.status_code) == (401, 401)


# Scenario: A wrong current password does not log anyone out
async def test_a_wrong_current_password_keeps_the_stored_version() -> None:
    async with _pg_env() as env:
        editor = await seed_user(_EDITOR_EMAIL, UserRole.EDITOR)
        async with env.client_for(editor) as client:
            refused = await client.post(
                CHANGE_URL, json=change_body("not-the-password", NEW_PASSWORD)
            )
            still_in = await client.get(ME_URL)

        assert refused.status_code == 401
        assert (await stored_user(editor.id)).token_version == 0
        assert still_in.status_code == 200


# Scenario: Concurrent password changes run one at a time
async def test_concurrent_changes_run_one_at_a_time() -> None:
    async with _pg_env() as env:
        editor = await seed_user(_EDITOR_EMAIL, UserRole.EDITOR)
        body = change_body(OLD_PASSWORD, NEW_PASSWORD)
        async with env.client() as first, env.client() as second:
            await sign_in(first, (_EDITOR_EMAIL, OLD_PASSWORD))
            await sign_in(second, (_EDITOR_EMAIL, OLD_PASSWORD))
            answers = await asyncio.gather(
                first.post(CHANGE_URL, json=body), second.post(CHANGE_URL, json=body)
            )
            after = [await client.get(ME_URL) for client in (first, second)]

        statuses = sorted(answer.status_code for answer in answers)
        assert statuses == [204, 401]
        assert (await stored_user(editor.id)).token_version == 1
        assert sorted(me.status_code for me in after) == [200, 401]


# Scenario: Two changes in a row bump the version twice
async def test_a_second_change_logs_out_the_token_of_the_first() -> None:
    async with _pg_env() as env:
        editor = await seed_user(_EDITOR_EMAIL, UserRole.EDITOR)
        async with env.client() as client:
            await sign_in(client, (_EDITOR_EMAIL, OLD_PASSWORD))
            once = await client.post(
                CHANGE_URL, json=change_body(OLD_PASSWORD, NEW_PASSWORD)
            )
            twice = await client.post(
                CHANGE_URL, json=change_body(NEW_PASSWORD, _THIRD_PASSWORD)
            )
            current = await client.get(ME_URL)
        first_token = {"Authorization": f"Bearer {once.cookies[_COOKIE_ACCESS]}"}
        async with env.client(first_token) as stale:
            refused = await stale.get(ME_URL)

        assert (once.status_code, twice.status_code) == (204, 204)
        assert (await stored_user(editor.id)).token_version == 2
        assert current.status_code == 200
        assert refused.status_code == 401


# Scenario: Two changes in a row bump the version twice
async def test_the_locked_read_serialises_two_writers() -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    async def bump_after_lock(session: AsyncSession) -> int:
        repo = PostgresUserRepository(session)
        user = await repo.get_by_id_for_update(editor.id)
        assert user is not None
        user.change_password(f"hash-after-{user.token_version}")
        saved = await repo.update(user)
        await session.commit()
        return saved.token_version

    async with _pg_env():
        editor = await seed_user(_EDITOR_EMAIL, UserRole.EDITOR)
        maker = get_session_maker()
        async with maker() as holder, maker() as waiter:
            held = await PostgresUserRepository(holder).get_by_id_for_update(editor.id)
            assert held is not None
            waiting = asyncio.create_task(bump_after_lock(waiter))
            await asyncio.sleep(_LOCK_WAIT_SECONDS)
            blocked = not waiting.done()
            held.change_password("hash-first")
            await PostgresUserRepository(holder).update(held)
            await holder.commit()
            second_version = await waiting

        assert blocked is True
        assert held.token_version == 1
        assert second_version == 2
        assert (await stored_user(editor.id)).token_version == 2
