"""The last-active-admin guard under concurrent updates, on real Postgres.

Scenarios: ``tests/features/last_active_admin_guard_ae0585.feature``. The guard
counts the active admins with their rows locked ``FOR UPDATE``, so two admins
deactivating each other at once are serialized instead of both reading two
active admins and leaving none. Skipped unless ``DATABASE_URL`` is Postgres.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
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
_FIRST_EMAIL = "lock-first@integration.example.com"
_SECOND_EMAIL = "lock-second@integration.example.com"
_BLOCKED_WAIT_SECONDS = 0.5
_ALLOWED = "ok"
_REFUSED = "refused"
_UNBLOCKED_WAIT_SECONDS = 10.0

pytestmark = [pytest.mark.integration, requires_postgres]


class _UnusedHasher:
    """Password hasher the update path never calls."""

    def hash_password(self, password: str) -> str:
        raise AssertionError(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        raise AssertionError((plain_password, hashed_password))


async def _seed_admin(engine: AsyncEngine, email: str) -> User:
    async with AsyncSession(engine) as session:
        user = User(
            email=email,
            full_name="Lock Admin",
            role=UserRole.ADMIN,
            hashed_password="not-used-in-tests",
        )
        created = await PostgresUserRepository(session).create(user)
        await session.commit()
    return created


async def _active_admins(engine: AsyncEngine) -> int:
    async with AsyncSession(engine) as session:
        return await PostgresUserRepository(session).count_active_by_role(
            UserRole.ADMIN
        )


async def _deactivate(engine: AsyncEngine, target: UUID) -> str:
    """Deactivate ``target`` in its own transaction; allowed or refused."""
    async with AsyncSession(engine) as session:
        handler = AdminUserHandler(
            PostgresUserRepository(session),
            AdminUserDeps(
                passwords=PasswordService(hasher=_UnusedHasher()),
                unit_of_work=SqlAlchemyUnitOfWork(session),
            ),
        )
        try:
            await handler.update(UpdateUserInput(user_id=target, is_active=False))
        except LastAdminError:
            return _REFUSED
    return _ALLOWED


class TestLastActiveAdminLock:
    """The active-admin count serializes concurrent admin updates."""

    # Scenario: Two admins deactivating each other at once leave one active admin
    async def test_mutual_deactivation_leaves_one_active_admin(self) -> None:
        async with isolated_schema(_TABLES) as engine:
            first = await _seed_admin(engine, _FIRST_EMAIL)
            second = await _seed_admin(engine, _SECOND_EMAIL)

            outcomes = await asyncio.gather(
                _deactivate(engine, second.id), _deactivate(engine, first.id)
            )

            assert sorted(outcomes) == sorted([_ALLOWED, _REFUSED])
            assert await _active_admins(engine) == 1

    # Scenario: The active-admin count locks the rows it counts
    async def test_a_second_count_waits_for_the_first_transaction(self) -> None:
        async with isolated_schema(_TABLES) as engine:
            await _seed_admin(engine, _FIRST_EMAIL)
            second = await _seed_admin(engine, _SECOND_EMAIL)
            async with AsyncSession(engine) as holder, AsyncSession(engine) as other:
                holder_repo = PostgresUserRepository(holder)
                assert await holder_repo.count_active_by_role(UserRole.ADMIN) == 2
                waiting = asyncio.create_task(
                    PostgresUserRepository(other).count_active_by_role(UserRole.ADMIN)
                )

                done, _ = await asyncio.wait({waiting}, timeout=_BLOCKED_WAIT_SECONDS)
                assert not done
                stored = await holder_repo.get_by_id(second.id)
                assert stored is not None
                stored.deactivate()
                await holder_repo.update(stored)
                await holder.commit()

                count = await asyncio.wait_for(waiting, _UNBLOCKED_WAIT_SECONDS)
                assert count == 1
                await other.rollback()
