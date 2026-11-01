"""Unit tests for the self-service password change and the forced change flag.

Scenarios: ``tests/features/change_own_password_ae0511.feature``. The fakes and
builders are the identity handler and service test doubles, whose repository
only persists on a Unit of Work commit, so a refused change is observable.
"""

from __future__ import annotations

import pytest

from rag_backend.modules.identity import (
    ChangePasswordCommand,
    CurrentPasswordIncorrectError,
    PasswordUnchangedError,
    User,
)
from tests.unit.modules.identity import test_identity_services as services
from tests.unit.modules.identity.test_identity_handlers import (
    _HASH_PREFIX,
    _VALID_PASSWORD,
    _build_admin_handler,
    _build_auth_handler,
    _seed_user,
)

_NEW_PASSWORD = "brand-new-passphrase"


def _command(user: User, current: str, new: str) -> ChangePasswordCommand:
    return ChangePasswordCommand(
        user_id=user.id, current_password=current, new_password=new
    )


@pytest.mark.unit
class TestUserPasswordMethods:
    """The aggregate sets or clears the flag with the new hash."""

    # Scenario: An admin reset makes the user change the password at next login
    def test_reset_password_stores_the_hash_and_sets_the_flag(self) -> None:
        user = User(email="a@example.com", full_name="A", hashed_password="old")

        user.reset_password("temp-hash")

        assert user.hashed_password == "temp-hash"
        assert user.must_change_password is True

    # Scenario: Changing a temporary password clears the flag
    def test_change_password_stores_the_hash_and_clears_the_flag(self) -> None:
        user = User(
            email="a@example.com",
            full_name="A",
            hashed_password="old",
            must_change_password=True,
        )

        user.change_password("new-hash")

        assert user.hashed_password == "new-hash"
        assert user.must_change_password is False


@pytest.mark.unit
class TestAuthHandlerChangePassword:
    """``AuthCommandHandler.change_password`` with the flag."""

    # Scenario: Changing a temporary password clears the flag
    async def test_a_flagged_user_changing_the_password_clears_the_flag(self) -> None:
        handler, repo, uow = _build_auth_handler()
        user = _seed_user(repo)
        user.must_change_password = True

        await handler.change_password(_command(user, _VALID_PASSWORD, _NEW_PASSWORD))

        stored = await repo.get_by_id(user.id)
        assert stored is not None
        assert stored.must_change_password is False
        assert stored.hashed_password == _HASH_PREFIX + _NEW_PASSWORD
        assert uow.commits == 1

    # Scenario: A signed-in user changes their own password
    async def test_a_normal_change_does_not_set_the_flag(self) -> None:
        handler, repo, _ = _build_auth_handler()
        user = _seed_user(repo)

        await handler.change_password(_command(user, _VALID_PASSWORD, _NEW_PASSWORD))

        stored = await repo.get_by_id(user.id)
        assert stored is not None
        assert stored.must_change_password is False

    # Scenario: A new password equal to the current one is refused
    async def test_the_same_password_is_refused_before_any_write(self) -> None:
        handler, repo, uow = _build_auth_handler()
        user = _seed_user(repo)
        user.must_change_password = True

        with pytest.raises(PasswordUnchangedError):
            await handler.change_password(
                _command(user, _VALID_PASSWORD, _VALID_PASSWORD)
            )

        assert uow.commits == 0
        assert user.must_change_password is True
        assert user.hashed_password == _HASH_PREFIX + _VALID_PASSWORD

    # Scenario: A wrong current password changes nothing
    async def test_a_wrong_current_password_keeps_the_flag(self) -> None:
        handler, repo, uow = _build_auth_handler()
        user = _seed_user(repo)
        user.must_change_password = True

        with pytest.raises(CurrentPasswordIncorrectError):
            await handler.change_password(_command(user, "wrong", "wrong"))

        assert uow.commits == 0
        assert user.must_change_password is True


@pytest.mark.unit
class TestAdminResetPasswordFlag:
    """``AdminUserHandler.reset_password`` flags the user."""

    # Scenario: An admin reset makes the user change the password at next login
    async def test_a_reset_flags_the_user_and_commits_once(self) -> None:
        handler, repo, uow = _build_admin_handler()
        user = _seed_user(repo)

        temp_password = await handler.reset_password(user.id)

        stored = await repo.get_by_id(user.id)
        assert stored is not None
        assert stored.must_change_password is True
        assert stored.hashed_password == _HASH_PREFIX + temp_password
        assert uow.commits == 1


@pytest.mark.unit
class TestUserServiceChangePassword:
    """``UserService.change_password`` follows the same rules."""

    # Scenario: Changing a temporary password clears the flag
    async def test_the_service_clears_the_flag(self) -> None:
        service, repo, uow = services._build_user_service()
        user = services._seed_user(repo)
        user.must_change_password = True

        await service.change_password(
            _command(user, services._VALID_PASSWORD, _NEW_PASSWORD)
        )

        assert user.must_change_password is False
        assert uow.commits == 1

    # Scenario: A new password equal to the current one is refused
    async def test_the_service_refuses_the_same_password(self) -> None:
        service, repo, uow = services._build_user_service()
        user = services._seed_user(repo)

        with pytest.raises(PasswordUnchangedError):
            await service.change_password(
                _command(user, services._VALID_PASSWORD, services._VALID_PASSWORD)
            )

        assert uow.commits == 0
