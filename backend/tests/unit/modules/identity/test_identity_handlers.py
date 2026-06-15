"""Unit tests for the identity inbound-adapter handlers (AE-0099).

Cover the auth + admin command/query handlers the thin ``/api/auth`` and
``/api/admin/users`` routes delegate to, exercised through the module facade with
fakes. The fakes model the transaction boundary explicitly (mirrors the AE-0098
service tests): the repository "flushes" into a staging buffer and only a UoW
``commit`` promotes staged rows, so the single-commit-owner contract (ADR-0009
§9) is observable. JWT/bcrypt are delegated to fakes here; the real
``infrastructure.auth`` delegation is wired in ``bootstrap.py`` and proven
byte-identical by the AE-0097 integration safety net.
"""

from __future__ import annotations

from types import TracebackType
from uuid import UUID, uuid4

import pytest

from rag_backend.modules.identity import (
    AdminUserDeps,
    AdminUserHandler,
    AuthCommandDeps,
    AuthCommandHandler,
    AuthenticationDeps,
    AuthenticationService,
    ChangePasswordCommand,
    CreateUserInput,
    CurrentPasswordIncorrectError,
    DeleteUserInput,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRoleError,
    LastAdminError,
    LoginCommand,
    PasswordService,
    SelfDeleteError,
    UpdateUserInput,
    User,
    UserAlreadyExistsError,
    UserNotFoundError,
    UserRole,
)

_HASH_PREFIX = "hash::"
_TOKEN_PREFIX = "token::"
_VALID_PASSWORD = "correct-horse-battery"  # >= MIN_PASSWORD_LENGTH (12)


# --- Fakes -------------------------------------------------------------------


class _SpyUnitOfWork:
    """UnitOfWork double recording commit/rollback and driving the store."""

    def __init__(self, repository: _FakeUserRepository) -> None:
        self._repository = repository
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1
        self._repository.flush_to_store()

    async def rollback(self) -> None:
        self.rollbacks += 1
        self._repository.discard_staged()

    async def __aenter__(self) -> _SpyUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
            return
        await self.commit()


class _FakeUserRepository:
    """Repository double that flushes into a staging buffer (no commit)."""

    def __init__(self) -> None:
        self.persisted: dict[UUID, User] = {}
        self._staged: dict[UUID, User] = {}

    def flush_to_store(self) -> None:
        self.persisted.update(self._staged)
        self._staged.clear()

    def discard_staged(self) -> None:
        self._staged.clear()

    async def create(self, user: User) -> User:
        self._staged[user.id] = user
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.persisted.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        for user in self.persisted.values():
            if user.email == email:
                return user
        return None

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        users = list(self.persisted.values())
        return users[offset : offset + limit]

    async def update(self, user: User) -> User:
        self._staged[user.id] = user
        return user

    async def delete(self, user_id: UUID) -> bool:
        if user_id not in self.persisted:
            return False
        del self.persisted[user_id]
        return True

    async def count(self) -> int:
        return len(self.persisted)

    async def count_by_role(self, role: UserRole) -> int:
        return sum(1 for u in self.persisted.values() if u.role == role)


class _FakePasswordHasher:
    """PasswordHasher double: prefix-hash + matching verify."""

    def hash_password(self, password: str) -> str:
        return _HASH_PREFIX + password

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return hashed_password == _HASH_PREFIX + plain_password


class _FakeTokenIssuer:
    """TokenIssuer double: prefix-token + reversible decode."""

    def create_access_token(self, user: User) -> str:
        return _TOKEN_PREFIX + str(user.id)

    def decode_access_token(self, token: str) -> dict[str, object] | None:
        if not token.startswith(_TOKEN_PREFIX):
            return None
        return {"sub": token.removeprefix(_TOKEN_PREFIX)}


# --- Builders ----------------------------------------------------------------


def _build_auth_handler() -> tuple[
    AuthCommandHandler, _FakeUserRepository, _SpyUnitOfWork
]:
    repo = _FakeUserRepository()
    uow = _SpyUnitOfWork(repo)
    passwords = PasswordService(hasher=_FakePasswordHasher())
    authentication = AuthenticationService(
        repository=repo,
        deps=AuthenticationDeps(passwords=passwords, tokens=_FakeTokenIssuer()),
    )
    handler = AuthCommandHandler(
        repository=repo,
        authentication=authentication,
        deps=AuthCommandDeps(passwords=passwords, unit_of_work=uow),
    )
    return handler, repo, uow


def _build_admin_handler() -> tuple[
    AdminUserHandler, _FakeUserRepository, _SpyUnitOfWork
]:
    repo = _FakeUserRepository()
    uow = _SpyUnitOfWork(repo)
    passwords = PasswordService(hasher=_FakePasswordHasher())
    handler = AdminUserHandler(
        repository=repo,
        deps=AdminUserDeps(passwords=passwords, unit_of_work=uow),
    )
    return handler, repo, uow


def _seed_user(
    repo: _FakeUserRepository,
    *,
    email: str = "user@example.com",
    role: UserRole = UserRole.EDITOR,
    is_active: bool = True,
) -> User:
    user = User(
        email=email,
        full_name="Test User",
        hashed_password=_HASH_PREFIX + _VALID_PASSWORD,
        role=role,
        is_active=is_active,
    )
    repo.persisted[user.id] = user
    return user


# --- AuthCommandHandler ------------------------------------------------------


@pytest.mark.unit
class TestAuthCommandHandler:
    async def test_login_returns_bearer_token(self) -> None:
        handler, repo, _ = _build_auth_handler()
        user = _seed_user(repo, email="login@example.com")

        view = await handler.login(
            LoginCommand(email="login@example.com", password=_VALID_PASSWORD)
        )

        assert view.access_token == _TOKEN_PREFIX + str(user.id)
        assert view.token_type == "bearer"

    async def test_login_invalid_credentials_raises(self) -> None:
        handler, repo, _ = _build_auth_handler()
        _seed_user(repo, email="login@example.com")

        with pytest.raises(InvalidCredentialsError):
            await handler.login(
                LoginCommand(email="login@example.com", password="wrong-password")
            )

    async def test_login_inactive_user_raises(self) -> None:
        handler, repo, _ = _build_auth_handler()
        _seed_user(repo, email="off@example.com", is_active=False)

        with pytest.raises(InactiveUserError):
            await handler.login(
                LoginCommand(email="off@example.com", password=_VALID_PASSWORD)
            )

    async def test_change_password_commits_once(self) -> None:
        handler, repo, uow = _build_auth_handler()
        user = _seed_user(repo)

        await handler.change_password(
            ChangePasswordCommand(
                user_id=user.id,
                current_password=_VALID_PASSWORD,
                new_password="brand-new-passphrase",
            )
        )

        assert uow.commits == 1
        stored = await repo.get_by_id(user.id)
        assert stored is not None
        assert stored.hashed_password == _HASH_PREFIX + "brand-new-passphrase"

    async def test_change_password_wrong_current_raises_before_write(self) -> None:
        handler, repo, uow = _build_auth_handler()
        user = _seed_user(repo)

        with pytest.raises(CurrentPasswordIncorrectError):
            await handler.change_password(
                ChangePasswordCommand(
                    user_id=user.id,
                    current_password="not-the-password",
                    new_password="brand-new-passphrase",
                )
            )

        # No write was attempted: nothing committed, hash unchanged.
        assert uow.commits == 0
        assert user.hashed_password == _HASH_PREFIX + _VALID_PASSWORD

    async def test_change_password_missing_user_raises(self) -> None:
        handler, _, _ = _build_auth_handler()

        with pytest.raises(UserNotFoundError):
            await handler.change_password(
                ChangePasswordCommand(
                    user_id=uuid4(),
                    current_password=_VALID_PASSWORD,
                    new_password="brand-new-passphrase",
                )
            )


# --- AdminUserHandler --------------------------------------------------------


@pytest.mark.unit
class TestAdminUserHandler:
    async def test_list_users_returns_total(self) -> None:
        handler, repo, _ = _build_admin_handler()
        _seed_user(repo, email="a@example.com")
        _seed_user(repo, email="b@example.com")

        listing = await handler.list_users()

        assert listing.total == 2
        assert {item.email for item in listing.items} == {
            "a@example.com",
            "b@example.com",
        }

    async def test_create_auto_generates_temp_password(self) -> None:
        handler, repo, uow = _build_admin_handler()

        created = await handler.create(
            CreateUserInput(
                email="new@example.com", full_name="New User", role="editor"
            )
        )

        assert created.temp_password is not None
        assert created.email == "new@example.com"
        assert uow.commits == 1
        stored = await repo.get_by_id(created.id)
        assert stored is not None
        assert stored.hashed_password == _HASH_PREFIX + created.temp_password

    async def test_create_with_password_has_no_temp(self) -> None:
        handler, _, _ = _build_admin_handler()

        created = await handler.create(
            CreateUserInput(
                email="custom@example.com",
                full_name="Custom",
                role="editor",
                password="MyCustomPass123!",
            )
        )

        assert created.temp_password is None

    async def test_create_invalid_role_raises_before_commit(self) -> None:
        handler, repo, uow = _build_admin_handler()

        with pytest.raises(InvalidRoleError) as exc_info:
            await handler.create(
                CreateUserInput(email="bad@example.com", full_name="Bad", role="wizard")
            )

        assert exc_info.value.role == "wizard"
        assert uow.commits == 0
        assert repo.persisted == {}

    async def test_create_duplicate_email_rolls_back(self) -> None:
        handler, repo, uow = _build_admin_handler()
        _seed_user(repo, email="dupe@example.com")

        with pytest.raises(UserAlreadyExistsError):
            await handler.create(
                CreateUserInput(
                    email="dupe@example.com", full_name="Dupe", role="editor"
                )
            )

        assert uow.rollbacks == 1
        assert len(repo.persisted) == 1

    async def test_update_role_uses_aggregate_mutator(self) -> None:
        handler, repo, uow = _build_admin_handler()
        user = _seed_user(repo, role=UserRole.EDITOR)
        before = user.updated_at

        view = await handler.update(UpdateUserInput(user_id=user.id, role="admin"))

        assert view.role == UserRole.ADMIN.value
        assert uow.commits == 1
        # set_role bumps updated_at (the legacy path that avoids the 500 defect).
        stored = await repo.get_by_id(user.id)
        assert stored is not None
        assert stored.updated_at > before

    async def test_update_is_active_toggles(self) -> None:
        handler, repo, _ = _build_admin_handler()
        user = _seed_user(repo, is_active=True)

        view = await handler.update(UpdateUserInput(user_id=user.id, is_active=False))

        assert view.is_active is False

    async def test_update_missing_user_before_role_validation(self) -> None:
        handler, _, _ = _build_admin_handler()

        # Missing user with an INVALID role must still raise UserNotFoundError
        # (legacy ordering: 404 before 422).
        with pytest.raises(UserNotFoundError):
            await handler.update(UpdateUserInput(user_id=uuid4(), role="wizard"))

    async def test_update_demote_last_admin_raises(self) -> None:
        handler, repo, _ = _build_admin_handler()
        admin = _seed_user(repo, email="admin@example.com", role=UserRole.ADMIN)

        with pytest.raises(LastAdminError):
            await handler.update(UpdateUserInput(user_id=admin.id, role="editor"))

    async def test_update_demote_with_second_admin_allowed(self) -> None:
        handler, repo, _ = _build_admin_handler()
        admin = _seed_user(repo, email="a1@example.com", role=UserRole.ADMIN)
        _seed_user(repo, email="a2@example.com", role=UserRole.ADMIN)

        view = await handler.update(UpdateUserInput(user_id=admin.id, role="editor"))

        assert view.role == UserRole.EDITOR.value

    async def test_delete_self_raises(self) -> None:
        handler, repo, _ = _build_admin_handler()
        admin = _seed_user(repo, role=UserRole.ADMIN)

        with pytest.raises(SelfDeleteError):
            await handler.delete(
                DeleteUserInput(user_id=admin.id, requested_by=admin.id)
            )

    async def test_delete_missing_user_raises(self) -> None:
        handler, _, _ = _build_admin_handler()

        with pytest.raises(UserNotFoundError):
            await handler.delete(DeleteUserInput(user_id=uuid4(), requested_by=uuid4()))

    async def test_delete_last_admin_raises(self) -> None:
        handler, repo, _ = _build_admin_handler()
        admin = _seed_user(repo, role=UserRole.ADMIN)

        with pytest.raises(LastAdminError):
            await handler.delete(
                DeleteUserInput(user_id=admin.id, requested_by=uuid4())
            )

    async def test_delete_editor_commits(self) -> None:
        handler, repo, uow = _build_admin_handler()
        editor = _seed_user(repo, role=UserRole.EDITOR)

        await handler.delete(DeleteUserInput(user_id=editor.id, requested_by=uuid4()))

        assert uow.commits == 1
        assert await repo.get_by_id(editor.id) is None

    async def test_reset_password_returns_new_temp_password(self) -> None:
        handler, repo, uow = _build_admin_handler()
        user = _seed_user(repo)
        old_hash = user.hashed_password

        temp_password = await handler.reset_password(user.id)

        assert temp_password
        assert uow.commits == 1
        stored = await repo.get_by_id(user.id)
        assert stored is not None
        assert stored.hashed_password == _HASH_PREFIX + temp_password
        assert stored.hashed_password != old_hash

    async def test_reset_password_missing_user_raises(self) -> None:
        handler, _, _ = _build_admin_handler()

        with pytest.raises(UserNotFoundError):
            await handler.reset_password(uuid4())
