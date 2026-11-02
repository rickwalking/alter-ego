"""A profile edit racing a password change, on real Postgres.

Scenarios: ``tests/features/stale_user_write_ae0596.feature``. Two sessions on
a throwaway schema: one holds the user row locked while it changes the
password, the other runs the admin edit. The edit must wait on the lock and,
once it runs, keep the new hash and the bumped token version. Skipped unless
``DATABASE_URL`` is Postgres (CI's backend test job does).
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from rag_backend.domain.models import User, UserRole
from rag_backend.infrastructure.database.user_repository import (
    PostgresUserRepository,
)
from rag_backend.modules.identity import (
    AdminUserDeps,
    AdminUserHandler,
    LastAdminError,
    PasswordService,
    UpdateUserInput,
)
from rag_backend.platform.database import SqlAlchemyUnitOfWork
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_TABLES = ("users",)
_OLD_HASH = "old-hash"
_NEW_HASH = "hash-of-the-change"
_NEW_NAME = "Renamed While Locked"
_STALE_NAME = "Renamed From A Stale Copy"
_POLL_SECONDS = 0.05
_POLL_ATTEMPTS = 100
_UNBLOCKED_WAIT_SECONDS = 10.0
_BOTH_EDITS = 2
_ALLOWED = "ok"
_REFUSED = "refused"
_LOCK_WAITERS_SQL = text(
    "SELECT count(*) FROM pg_stat_activity"
    " WHERE datname = current_database() AND wait_event_type = 'Lock'"
)

pytestmark = [pytest.mark.integration, requires_postgres]


class _UnusedHasher:
    """Password hasher the edit path never calls."""

    def hash_password(self, password: str) -> str:
        raise AssertionError(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        raise AssertionError((plain_password, hashed_password))


async def _seed_editor(engine: AsyncEngine) -> User:
    async with AsyncSession(engine) as session:
        user = User(
            email="stale-pg@integration.example.com",
            full_name="Before",
            role=UserRole.EDITOR,
            hashed_password=_OLD_HASH,
        )
        created = await PostgresUserRepository(session).create(user)
        await session.commit()
    return created


async def _stored(engine: AsyncEngine, user_id: UUID) -> User:
    async with AsyncSession(engine) as session:
        stored = await PostgresUserRepository(session).get_by_id(user_id)
    assert stored is not None
    return stored


async def _seed_admin(engine: AsyncEngine, email: str) -> User:
    async with AsyncSession(engine) as session:
        user = User(
            email=email,
            full_name="Order Admin",
            role=UserRole.ADMIN,
            hashed_password=_OLD_HASH,
        )
        created = await PostgresUserRepository(session).create(user)
        await session.commit()
    return created


async def _edit_by_admin(engine: AsyncEngine, edit: UpdateUserInput) -> None:
    """Run the admin edit in its own session and transaction."""
    async with AsyncSession(engine) as session:
        handler = AdminUserHandler(
            PostgresUserRepository(session),
            AdminUserDeps(
                passwords=PasswordService(hasher=_UnusedHasher()),
                unit_of_work=SqlAlchemyUnitOfWork(session),
            ),
        )
        await handler.update(edit)


async def _deactivate(engine: AsyncEngine, user_id: UUID) -> str:
    """Deactivate ``user_id`` through the admin edit; allowed or refused."""
    try:
        await _edit_by_admin(engine, UpdateUserInput(user_id=user_id, is_active=False))
    except LastAdminError:
        return _REFUSED
    return _ALLOWED


async def _wait_for_lock_waiters(engine: AsyncEngine, minimum: int) -> bool:
    """Poll Postgres until ``minimum`` backends of this database wait on a lock."""
    async with AsyncSession(engine) as probe:
        for _ in range(_POLL_ATTEMPTS):
            waiters = (await probe.execute(_LOCK_WAITERS_SQL)).scalar_one()
            await probe.rollback()
            if waiters >= minimum:
                return True
            await asyncio.sleep(_POLL_SECONDS)
    return False


# Scenario: An admin profile edit waits for a password change that holds the user row
async def test_an_admin_rename_waits_and_keeps_the_password_change() -> None:
    async with isolated_schema(_TABLES) as engine:
        editor = await _seed_editor(engine)
        async with AsyncSession(engine) as holder:
            repo = PostgresUserRepository(holder)
            held = await repo.get_by_id_for_update(editor.id)
            assert held is not None
            renaming = asyncio.create_task(
                _edit_by_admin(
                    engine, UpdateUserInput(user_id=editor.id, full_name=_NEW_NAME)
                )
            )
            waiting = await _wait_for_lock_waiters(engine, 1)
            pending = not renaming.done()
            name_while_held = (await _stored(engine, editor.id)).full_name
            held.change_password(_NEW_HASH)
            await repo.update(held)
            await holder.commit()
            await asyncio.wait_for(renaming, _UNBLOCKED_WAIT_SECONDS)

        stored = await _stored(engine, editor.id)
        assert (waiting, pending, name_while_held) == (True, True, "Before")
        assert stored.full_name == _NEW_NAME
        assert (stored.hashed_password, stored.token_version) == (_NEW_HASH, 1)


# Scenario: A stale profile edit keeps the new password and token version
async def test_a_stale_copy_saved_after_a_change_keeps_the_new_credentials() -> None:
    async with isolated_schema(_TABLES) as engine:
        editor = await _seed_editor(engine)
        async with AsyncSession(engine) as stale_session:
            stale_repo = PostgresUserRepository(stale_session)
            stale = await stale_repo.get_by_id(editor.id)
            assert stale is not None
            async with AsyncSession(engine) as changer:
                changer_repo = PostgresUserRepository(changer)
                changing = await changer_repo.get_by_id_for_update(editor.id)
                assert changing is not None
                changing.change_password(_NEW_HASH)
                await changer_repo.update(changing)
                await changer.commit()
            stale.rename(_STALE_NAME)
            await stale_repo.update(stale)
            await stale_session.commit()

        stored = await _stored(engine, editor.id)
        assert stored.full_name == _STALE_NAME
        assert (stored.hashed_password, stored.token_version) == (_NEW_HASH, 1)


# Scenario: Admin edits queued behind a password change never deadlock
async def test_admin_edits_queued_behind_a_change_never_deadlock() -> None:
    async with isolated_schema(_TABLES) as engine:
        first = await _seed_admin(engine, "order-first@integration.example.com")
        second = await _seed_admin(engine, "order-second@integration.example.com")
        async with AsyncSession(engine) as holder:
            repo = PostgresUserRepository(holder)
            held = await repo.get_by_id_for_update(first.id)
            assert held is not None
            edits = asyncio.gather(
                _deactivate(engine, second.id), _deactivate(engine, first.id)
            )
            waiting = await _wait_for_lock_waiters(engine, _BOTH_EDITS)
            held.change_password(_NEW_HASH)
            await repo.update(held)
            await holder.commit()
            outcomes = await asyncio.wait_for(edits, _UNBLOCKED_WAIT_SECONDS)

        assert waiting is True
        assert sorted(outcomes) == sorted([_ALLOWED, _REFUSED])
        still_active = [
            (await _stored(engine, u.id)).is_active for u in (first, second)
        ]
        assert still_active.count(True) == 1
