"""User repository updates on real Postgres.

Gherkin: tests/features/user_password_update.feature
  Scenario: A password-only update is saved and returned on Postgres
  Scenario: An update keeps an explicitly bumped updated_at

Runs the repository against a real async session (no mocks), so a lazy load
of a server-generated column after the flush fails here exactly as it did in
the routes. Skipped unless ``DATABASE_URL`` points at Postgres.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.domain.models import User, UserRole
from rag_backend.infrastructure.database.user_repository import (
    PostgresUserRepository,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

pytestmark = [pytest.mark.integration, requires_postgres]

_TABLES = ("users",)
_OLD_HASH = "old-hash"
_NEW_HASH = "new-hash"
_BUMP = timedelta(minutes=5)


def _maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def _seed(maker: async_sessionmaker[AsyncSession]) -> User:
    async with maker() as session:
        user = User(
            email="pg-update@example.com",
            full_name="Pg Update",
            hashed_password=_OLD_HASH,
            role=UserRole.EDITOR,
        )
        created = await PostgresUserRepository(session).create(user)
        await session.commit()
        return created


async def _reload(maker: async_sessionmaker[AsyncSession], user: User) -> User:
    async with maker() as session:
        stored = await PostgresUserRepository(session).get_by_id(user.id)
    assert stored is not None
    return stored


@pytest.mark.asyncio
async def test_password_only_update_is_saved_and_returned() -> None:
    """Scenario: A password-only update is saved and returned on Postgres."""
    async with isolated_schema(_TABLES) as engine:
        maker = _maker(engine)
        seeded = await _seed(maker)
        async with maker() as session:
            repository = PostgresUserRepository(session)
            user = await repository.get_by_id(seeded.id)
            assert user is not None
            user.hashed_password = _NEW_HASH
            updated = await repository.update(user)
            await session.commit()

        stored = await _reload(maker, seeded)
        assert updated.hashed_password == _NEW_HASH
        assert stored.hashed_password == _NEW_HASH
        assert updated.updated_at == stored.updated_at
        assert stored.updated_at >= seeded.updated_at


@pytest.mark.asyncio
async def test_update_keeps_an_explicit_updated_at() -> None:
    """Scenario: An update keeps an explicitly bumped updated_at."""
    async with isolated_schema(_TABLES) as engine:
        maker = _maker(engine)
        seeded = await _seed(maker)
        bumped = seeded.updated_at + _BUMP
        async with maker() as session:
            repository = PostgresUserRepository(session)
            user = await repository.get_by_id(seeded.id)
            assert user is not None
            user.set_role(UserRole.ADMIN)
            user.updated_at = bumped
            updated = await repository.update(user)
            await session.commit()

        stored = await _reload(maker, seeded)
        assert updated.role == UserRole.ADMIN
        assert stored.role == UserRole.ADMIN
        assert stored.updated_at == bumped
