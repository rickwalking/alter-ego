"""Token versions on real Postgres: the logout flow and the repository write.

Scenarios: ``tests/features/logout_other_sessions_ae0593.feature``. Runs the
real app against a throwaway Postgres schema holding the users and
conversations tables, so the version is the real column the production adapter
reads and writes. Skipped unless ``DATABASE_URL`` points at Postgres (CI's
backend test job does).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest

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


# Scenario: An older write never lowers the token version
async def test_an_update_read_before_a_change_keeps_the_newer_version() -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    async with _pg_env() as env:
        editor = await seed_user(_EDITOR_EMAIL, UserRole.EDITOR)
        read_before = await stored_user(editor.id)
        async with env.client_for(editor) as client:
            changed = await client.post(
                CHANGE_URL, json=change_body(OLD_PASSWORD, NEW_PASSWORD)
            )
        read_before.rename("Renamed Later")
        async with get_session_maker()() as session:
            saved = await PostgresUserRepository(session).update(read_before)
            await session.commit()

        assert changed.status_code == 204
        assert saved.token_version == 1
        stored = await stored_user(editor.id)
        assert stored.token_version == 1
        assert stored.full_name == "Renamed Later"
