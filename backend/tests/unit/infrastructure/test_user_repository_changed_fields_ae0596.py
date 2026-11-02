"""The user repository saves only the fields an entity changed.

Scenarios: ``tests/features/stale_user_write_ae0596.feature``. Runs the real
``PostgresUserRepository`` on the SQLite test database: a copy of the user read
before a password change, saved after it, must not put back the old hash or the
old token version.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models import User
from rag_backend.infrastructure.database.models import UserModel
from rag_backend.infrastructure.database.user_repository import (
    PostgresUserRepository,
)

_OLD_HASH = "old-hash"
_NEW_HASH = "new-hash"
_OUTSIDE_HASH = "hash-written-elsewhere"
_NEW_NAME = "Renamed After"

pytestmark = pytest.mark.unit


async def _seed(repo: PostgresUserRepository, session: AsyncSession) -> User:
    user = User(
        email="stale@example.com", full_name="Before", hashed_password=_OLD_HASH
    )
    created = await repo.create(user)
    await session.commit()
    return created


async def _stored(repo: PostgresUserRepository, user_id: UUID) -> User:
    stored = await repo.get_by_id_for_update(user_id)
    assert stored is not None
    return stored


# Scenario: A stale profile edit keeps the new password and token version
async def test_a_stale_rename_keeps_the_new_hash_and_version(
    db_session: AsyncSession,
) -> None:
    repo = PostgresUserRepository(db_session)
    seeded = await _seed(repo, db_session)
    stale = await repo.get_by_id(seeded.id)
    assert stale is not None
    changing = await _stored(repo, seeded.id)
    changing.change_password(_NEW_HASH)
    await repo.update(changing)
    await db_session.commit()

    stale.rename(_NEW_NAME)
    saved = await repo.update(stale)
    await db_session.commit()

    stored = await _stored(repo, seeded.id)
    assert stored.full_name == _NEW_NAME
    assert (stored.hashed_password, stored.token_version) == (_NEW_HASH, 1)
    assert stored.must_change_password is False
    assert (saved.hashed_password, saved.token_version) == (_NEW_HASH, 1)


# Scenario: A save with no changed field writes no column
async def test_a_save_with_nothing_changed_writes_no_column(
    db_session: AsyncSession,
) -> None:
    repo = PostgresUserRepository(db_session)
    seeded = await _seed(repo, db_session)
    loaded = await repo.get_by_id(seeded.id)
    assert loaded is not None
    await db_session.execute(
        update(UserModel)
        .where(UserModel.id == str(seeded.id))
        .values(hashed_password=_OUTSIDE_HASH, full_name="Elsewhere")
    )

    await repo.update(loaded)

    stored = await _stored(repo, seeded.id)
    assert (stored.hashed_password, stored.full_name) == (_OUTSIDE_HASH, "Elsewhere")


# Scenario: Every assigned persisted field is reported changed
async def test_a_direct_assignment_is_saved(db_session: AsyncSession) -> None:
    repo = PostgresUserRepository(db_session)
    seeded = await _seed(repo, db_session)
    loaded = await _stored(repo, seeded.id)

    loaded.token_version = 7
    await repo.update(loaded)

    assert (await _stored(repo, seeded.id)).token_version == 7
