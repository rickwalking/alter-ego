"""An admin reset on real Postgres: the logout flow and the row lock.

Scenarios: ``tests/features/admin_reset_logs_out_ae0595.feature``. Runs the
real app against a throwaway Postgres schema holding the users and
conversations tables, so the version is the real column the production adapter
reads and writes, and the row lock the reset takes is a real Postgres lock.
Skipped unless ``DATABASE_URL`` points at Postgres (CI's backend test job does).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text

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
    reset_by_admin,
    seed_user,
    stored_user,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_TABLES = ("users", "conversations", "messages")
_ADMIN_EMAIL = "reset-pg-admin@integration.example.com"
_EDITOR_EMAIL = "reset-pg-editor@integration.example.com"
_POLL_SECONDS = 0.05
_POLL_ATTEMPTS = 100
_LOCK_WAITERS_SQL = text(
    "SELECT count(*) FROM pg_stat_activity"
    " WHERE datname = current_database() AND wait_event_type = 'Lock'"
)

pytestmark = [pytest.mark.integration, requires_postgres]


@asynccontextmanager
async def _pg_env() -> AsyncIterator[FlowEnv]:
    """The real app over a fresh Postgres schema (opened inside each test)."""
    async with isolated_schema(_TABLES) as engine, app_over(engine) as env:
        yield env


async def _wait_for_a_lock_waiter() -> bool:
    """Poll Postgres until some backend of this database waits on a lock."""
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as probe:
        for _ in range(_POLL_ATTEMPTS):
            waiters = (await probe.execute(_LOCK_WAITERS_SQL)).scalar_one()
            await probe.rollback()
            if waiters > 0:
                return True
            await asyncio.sleep(_POLL_SECONDS)
    return False


# Scenario: An admin reset logs out every open session of the user
async def test_a_reset_on_postgres_logs_out_the_user_only() -> None:
    async with _pg_env() as env:
        admin = await seed_user(_ADMIN_EMAIL, UserRole.ADMIN)
        editor = await seed_user(_EDITOR_EMAIL, UserRole.EDITOR)
        editor_login = await login(env, (_EDITOR_EMAIL, OLD_PASSWORD))
        admin_login = await login(env, (_ADMIN_EMAIL, OLD_PASSWORD))
        async with (
            env.client(bearer(editor_login)) as user_session,
            env.client(bearer(admin_login)) as admin_session,
        ):
            reset = await admin_session.post(
                f"/api/admin/users/{editor.id}/reset-password"
            )
            user_me = await user_session.get(ME_URL)
            user_change = await user_session.post(
                CHANGE_URL, json=change_body(OLD_PASSWORD, NEW_PASSWORD)
            )
            user_list = await user_session.get(CONVERSATIONS_URL)
            admin_me = await admin_session.get(ME_URL)
        temp_login = await login(env, (_EDITOR_EMAIL, reset.json()["temp_password"]))

        assert reset.status_code == 200
        assert (user_me.status_code, user_change.status_code) == (401, 401)
        assert user_list.status_code == 401
        assert admin_me.status_code == 200
        assert temp_login.status_code == 200
        stored = await stored_user(editor.id)
        assert (stored.token_version, stored.must_change_password) == (1, True)
        assert (await stored_user(admin.id)).token_version == 0


# Scenario: A reset waits for a password change that holds the user row
async def test_the_reset_waits_for_the_row_lock_and_bumps_from_the_commit() -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    async with _pg_env() as env:
        admin = await seed_user(_ADMIN_EMAIL, UserRole.ADMIN)
        editor = await seed_user(_EDITOR_EMAIL, UserRole.EDITOR)
        async with get_session_maker()() as holder:
            repo = PostgresUserRepository(holder)
            held = await repo.get_by_id_for_update(editor.id)
            assert held is not None
            resetting = asyncio.create_task(reset_by_admin(env, admin, editor))
            waiting = await _wait_for_a_lock_waiter()
            pending = not resetting.done()
            version_while_held = (await stored_user(editor.id)).token_version
            held.change_password("hash-of-the-change")
            await repo.update(held)
            await holder.commit()
            temp_password = await resetting
        temp_login = await login(env, (_EDITOR_EMAIL, temp_password))

        assert (waiting, pending) == (True, True)
        assert version_while_held == 0
        assert (await stored_user(editor.id)).token_version == 2
        assert temp_login.status_code == 200
