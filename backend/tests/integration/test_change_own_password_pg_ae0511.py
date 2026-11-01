"""The admin reset and forced password change flow on real Postgres.

Scenarios: ``tests/features/change_own_password_ae0511.feature``. Runs the real
app against a throwaway Postgres schema holding the users and conversations
tables, so the flag is the real column the production adapter reads and
writes. Skipped unless ``DATABASE_URL`` points at Postgres (CI's backend test
job does).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest

from rag_backend.domain.models import UserRole
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
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_TABLES = ("users", "conversations", "messages")
_ADMIN_EMAIL = "flow-admin@integration.example.com"
_EDITOR_EMAIL = "flow-editor@integration.example.com"

pytestmark = [pytest.mark.integration, requires_postgres]


@asynccontextmanager
async def _pg_env() -> AsyncIterator[FlowEnv]:
    """The real app over a fresh Postgres schema (opened inside each test)."""
    async with isolated_schema(_TABLES) as engine, app_over(engine) as env:
        yield env


# Scenario: The full reset and change flow on Postgres
async def test_reset_login_refused_change_then_allowed() -> None:
    async with _pg_env() as env:
        admin = await seed_user(_ADMIN_EMAIL, UserRole.ADMIN)
        editor = await seed_user(_EDITOR_EMAIL, UserRole.EDITOR)

        temp = await reset_by_admin(env, admin, editor)
        assert (await stored_user(editor.id)).must_change_password is True
        token = await login(env, (_EDITOR_EMAIL, temp))
        assert token.status_code == 200
        async with env.client(bearer(token)) as client:
            refused = await client.get(CONVERSATIONS_URL)
            flagged_me = await client.get(ME_URL)
            changed = await client.post(
                CHANGE_URL, json=change_body(temp, NEW_PASSWORD)
            )
            allowed = await client.get(CONVERSATIONS_URL)
            cleared_me = await client.get(ME_URL)

        assert refused.status_code == 403
        assert refused.json()["code"] == CODE_CHANGE_REQUIRED
        assert flagged_me.json()["must_change_password"] is True
        assert changed.status_code == 204
        assert (await stored_user(editor.id)).must_change_password is False
        assert allowed.status_code == 200
        assert cleared_me.json()["must_change_password"] is False
        assert (await login(env, (_EDITOR_EMAIL, temp))).status_code == 401
        assert (await login(env, (_EDITOR_EMAIL, NEW_PASSWORD))).status_code == 200


# Scenario: A wrong current password on Postgres leaves the user unchanged
async def test_a_wrong_current_password_leaves_the_stored_user_unchanged() -> None:
    async with _pg_env() as env:
        editor = await seed_user(_EDITOR_EMAIL, UserRole.EDITOR)

        async with env.client_for(editor) as client:
            resp = await client.post(
                CHANGE_URL, json=change_body("not-the-password", NEW_PASSWORD)
            )

        assert resp.status_code == 401
        assert resp.json()["code"] == "current_password_incorrect"
        stored = await stored_user(editor.id)
        assert stored.hashed_password == editor.hashed_password
        assert stored.must_change_password is False
        assert (await login(env, (_EDITOR_EMAIL, OLD_PASSWORD))).status_code == 200
