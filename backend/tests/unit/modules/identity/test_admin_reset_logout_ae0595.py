"""Unit tests for the admin reset that logs out the user's open sessions.

Scenarios: ``tests/features/admin_reset_logs_out_ae0595.feature``. The handler
fakes are the identity test doubles, whose repository only persists on a Unit
of Work commit and records every locked read.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from rag_backend.modules.identity import User, UserNotFoundError
from tests.unit.modules.identity.test_identity_handlers import (
    _HASH_PREFIX,
    _build_admin_handler,
    _seed_user,
)

_TEMP_HASH = "temp-hash"

pytestmark = pytest.mark.unit


def _user(token_version: int) -> User:
    return User(
        email="reset@example.com",
        full_name="Reset",
        hashed_password="old-hash",
        token_version=token_version,
    )


# Scenario: An admin reset bumps the token version in the same write
def test_the_entity_reset_bumps_the_version_with_the_new_hash() -> None:
    user = _user(token_version=2)

    user.reset_password(_TEMP_HASH)

    assert user.hashed_password == _TEMP_HASH
    assert user.must_change_password is True
    assert user.token_version == 3


# Scenario: An admin reset bumps the token version in the same write
async def test_the_handler_commits_the_bump_once_from_a_locked_read() -> None:
    handler, repo, uow = _build_admin_handler()
    user = _seed_user(repo)
    user.token_version = 2

    temp_password = await handler.reset_password(user.id)

    stored = await repo.get_by_id(user.id)
    assert stored is not None
    assert stored.hashed_password == _HASH_PREFIX + temp_password
    assert stored.must_change_password is True
    assert stored.token_version == 3
    assert uow.commits == 1
    assert repo.locked == [user.id]


# Scenario: A reset of an unknown user changes no token version
async def test_a_reset_of_an_unknown_user_commits_nothing() -> None:
    handler, repo, uow = _build_admin_handler()
    user = _seed_user(repo)
    missing = uuid4()

    with pytest.raises(UserNotFoundError):
        await handler.reset_password(missing)

    assert user.token_version == 0
    assert uow.commits == 0
    assert uow.rollbacks == 1
    assert repo.locked == [missing]
