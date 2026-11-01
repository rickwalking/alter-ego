"""Unit tests for the token version that logs out other sessions.

Scenarios: ``tests/features/logout_other_sessions_ae0593.feature``. The handler
and service fakes are the identity test doubles, whose repository only
persists on a Unit of Work commit, so a refused change is observable.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import jwt
import pytest
from fastapi import HTTPException

from rag_backend.api.dependencies.auth import get_optional_user, require_signed_in_user
from rag_backend.api.dependencies.roles import get_current_user
from rag_backend.api.dependencies.token_version import (
    claimed_token_version,
    is_current_token,
    reject_stale_token,
)
from rag_backend.domain.constants import JWT_ALGORITHM
from rag_backend.infrastructure.auth import create_access_token, decode_access_token
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.identity import (
    ChangePasswordCommand,
    CurrentPasswordIncorrectError,
    PasswordUnchangedError,
    User,
)
from tests.unit.modules.identity import test_identity_services as services
from tests.unit.modules.identity.test_identity_handlers import (
    _TOKEN_PREFIX,
    _VALID_PASSWORD,
    _build_auth_handler,
    _seed_user,
)

_NEW_PASSWORD = "brand-new-passphrase"
_STALE_DETAIL = "Invalid or expired token"


def _command(user: User, current: str, new: str) -> ChangePasswordCommand:
    return ChangePasswordCommand(
        user_id=user.id, current_password=current, new_password=new
    )


def _user(token_version: int) -> User:
    return User(
        email="tv@example.com",
        full_name="TV",
        hashed_password="hash",
        token_version=token_version,
    )


def _payload(user: User, claims: dict[str, object]) -> dict[str, object]:
    return {"sub": str(user.id), **claims}


class _Repo:
    """User repository double answering ``get_by_id`` with one user."""

    def __init__(self, user: User) -> None:
        self._user = user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._user if user_id == self._user.id else None


@pytest.mark.unit
class TestIssuedToken:
    # Scenario: A new token carries the user's current token version
    def test_a_new_token_carries_the_user_token_version(self) -> None:
        settings = get_settings()
        token = create_access_token(settings, _user(3))

        payload = decode_access_token(settings, token)

        assert payload is not None
        assert payload["tv"] == 3


@pytest.mark.unit
class TestClaimedTokenVersion:
    # Scenario: A token without a token version still works for a user at version 0
    def test_a_token_without_tv_counts_as_version_0(self) -> None:
        assert claimed_token_version({"sub": "u"}) == 0
        assert is_current_token({"sub": "u"}, 0) is True

    # Scenario: A token without a token version is refused once the user changed the password
    def test_a_token_without_tv_is_stale_after_a_change(self) -> None:
        assert is_current_token({"sub": "u"}, 1) is False

    # Scenario: A token whose tv is not a whole number is refused
    @pytest.mark.parametrize("value", ["0", 0.0, True, None])
    def test_a_tv_that_is_not_a_whole_number_is_malformed(self, value: object) -> None:
        assert claimed_token_version({"tv": value}) is None
        assert is_current_token({"tv": value}, 0) is False

    # Scenario: Every other session is logged out by a password change
    def test_a_stale_token_is_refused_like_an_expired_one(self) -> None:
        reject_stale_token({"tv": 2}, 2)

        with pytest.raises(HTTPException) as exc_info:
            reject_stale_token({"tv": 1}, 2)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == _STALE_DETAIL
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.unit
class TestUserLoadingDependencies:
    """Each dependency that loads the user refuses a stale token."""

    # Scenario: Every other session is logged out by a password change
    async def test_require_signed_in_user_refuses_a_stale_token(self) -> None:
        user = _user(1)
        repo = _Repo(user)

        accepted = await require_signed_in_user(_payload(user, {"tv": 1}), repo)
        with pytest.raises(HTTPException) as exc_info:
            await require_signed_in_user(_payload(user, {"tv": 0}), repo)

        assert accepted is user
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == _STALE_DETAIL

    # Scenario: Every other session is logged out by a password change
    async def test_get_optional_user_treats_a_stale_token_as_a_visitor(self) -> None:
        user = _user(1)
        repo = _Repo(user)

        assert await get_optional_user(_payload(user, {"tv": 1}), repo) is user
        assert await get_optional_user(_payload(user, {}), repo) is None

    # Scenario: Every other session is logged out by a password change
    async def test_role_guarded_user_refuses_a_stale_token(self) -> None:
        db = AsyncMock()
        model = MagicMock(is_active=True, must_change_password=False, token_version=2)
        db.get = AsyncMock(return_value=model)

        assert await get_current_user({"sub": "u", "tv": 2}, db) is model
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user({"sub": "u", "tv": 1}, db)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == _STALE_DETAIL

    # Scenario: Every other session is logged out by a password change
    async def test_a_stale_token_is_refused_before_the_forced_change_check(
        self,
    ) -> None:
        db = AsyncMock()
        flagged = MagicMock(is_active=True, must_change_password=True, token_version=1)
        db.get = AsyncMock(return_value=flagged)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user({"sub": "u"}, db)

        assert exc_info.value.status_code == 401


@pytest.mark.unit
class TestChangePasswordBumpsTheVersion:
    # Scenario: A password change bumps the token version in the same write
    def test_the_entity_bumps_the_version_with_the_new_hash(self) -> None:
        user = _user(4)
        user.must_change_password = True

        user.change_password("new-hash")

        assert user.hashed_password == "new-hash"
        assert user.token_version == 5
        assert user.must_change_password is False

    # Scenario: A password change bumps the token version in the same write
    async def test_the_handler_commits_the_bump_once_and_issues_a_token(self) -> None:
        handler, repo, uow = _build_auth_handler()
        user = _seed_user(repo)

        token = await handler.change_password(
            _command(user, _VALID_PASSWORD, _NEW_PASSWORD)
        )

        stored = await repo.get_by_id(user.id)
        assert stored is not None
        assert stored.token_version == 1
        assert uow.commits == 1
        assert token.access_token == _TOKEN_PREFIX + str(user.id)

    # Scenario: A wrong current password does not log anyone out
    async def test_a_wrong_current_password_keeps_the_version(self) -> None:
        handler, repo, uow = _build_auth_handler()
        user = _seed_user(repo)

        with pytest.raises(CurrentPasswordIncorrectError):
            await handler.change_password(_command(user, "wrong", _NEW_PASSWORD))

        assert user.token_version == 0
        assert uow.commits == 0

    # Scenario: Reusing the current password does not log anyone out
    async def test_reusing_the_current_password_keeps_the_version(self) -> None:
        handler, repo, uow = _build_auth_handler()
        user = _seed_user(repo)

        with pytest.raises(PasswordUnchangedError):
            await handler.change_password(
                _command(user, _VALID_PASSWORD, _VALID_PASSWORD)
            )

        assert user.token_version == 0
        assert uow.commits == 0

    # Scenario: A password change bumps the token version in the same write
    async def test_the_user_service_bumps_the_version_too(self) -> None:
        service, repo, uow = services._build_user_service()
        user = services._seed_user(repo)

        await service.change_password(
            _command(user, services._VALID_PASSWORD, _NEW_PASSWORD)
        )

        stored = await repo.get_by_id(user.id)
        assert stored is not None
        assert stored.token_version == 1
        assert uow.commits == 1


@pytest.mark.unit
class TestTokenWithoutVersion:
    # Scenario: A token without a token version still works for a user at version 0
    def test_a_pre_versioning_token_decodes_without_tv(self) -> None:
        settings = get_settings()
        user = _user(0)
        token = jwt.encode(
            {"sub": str(user.id), "type": "auth", "exp": 4102444800},
            settings.secret_key.get_secret_value(),
            algorithm=JWT_ALGORITHM,
        )

        payload = decode_access_token(settings, token)

        assert payload is not None
        assert "tv" not in payload
        assert is_current_token(payload, user.token_version) is True
