"""Unit tests for the identity application services (AE-0098).

Cover the three extracted services through the module facade with fakes:
``UserService`` (CRUD + role assign, committed once through the injected Unit of
Work), ``AuthenticationService`` (login success + the legacy bad-credentials /
inactive-account failures + token issue/validate), and ``PasswordService``
(hash/verify + minimum-length policy). The fakes model the transaction boundary
explicitly (mirrors the AE-0091 knowledge UoW tests): the repository "flushes"
into a staging buffer, and only a UoW ``commit`` promotes staged rows. JWT/bcrypt
are delegated to fakes here; the real ``infrastructure.auth`` delegation is wired
in ``bootstrap.py`` and proven type-clean by mypy.
"""

from __future__ import annotations

from types import TracebackType
from uuid import UUID, uuid4

import pytest

from rag_backend.modules.identity import (
    AssignRoleCommand,
    AuthenticationDeps,
    AuthenticationService,
    ChangePasswordCommand,
    CreateUserCommand,
    CurrentPasswordIncorrectError,
    DeleteUserCommand,
    GetUserQuery,
    InactiveUserError,
    InvalidCredentialsError,
    ListUsersQuery,
    LoginCommand,
    PasswordService,
    UpdateUserCommand,
    User,
    UserNotFoundError,
    UserRole,
    UserService,
    UserServiceDeps,
)

_HASH_PREFIX = "hash::"
_TOKEN_PREFIX = "token::"
_VALID_PASSWORD = "correct-horse-battery"  # >= MIN_PASSWORD_LENGTH (12)
_SHORT_PASSWORD = "short"


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


def _build_user_service() -> tuple[UserService, _FakeUserRepository, _SpyUnitOfWork]:
    repo = _FakeUserRepository()
    uow = _SpyUnitOfWork(repo)
    passwords = PasswordService(hasher=_FakePasswordHasher())
    service = UserService(
        repository=repo,
        deps=UserServiceDeps(passwords=passwords, unit_of_work=uow),
    )
    return service, repo, uow


def _build_auth_service() -> tuple[AuthenticationService, _FakeUserRepository]:
    repo = _FakeUserRepository()
    passwords = PasswordService(hasher=_FakePasswordHasher())
    service = AuthenticationService(
        repository=repo,
        deps=AuthenticationDeps(passwords=passwords, tokens=_FakeTokenIssuer()),
    )
    return service, repo


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


# --- PasswordService ---------------------------------------------------------


@pytest.mark.unit
class TestPasswordService:
    def test_hash_then_verify_round_trip(self) -> None:
        service = PasswordService(hasher=_FakePasswordHasher())

        hashed = service.hash(_VALID_PASSWORD)

        assert service.verify(_VALID_PASSWORD, hashed) is True
        assert service.verify("wrong-password", hashed) is False

    def test_hash_rejects_short_password(self) -> None:
        service = PasswordService(hasher=_FakePasswordHasher())

        with pytest.raises(ValueError):
            service.hash(_SHORT_PASSWORD)

    def test_policy_helpers(self) -> None:
        assert PasswordService.meets_policy(_VALID_PASSWORD) is True
        assert PasswordService.meets_policy(_SHORT_PASSWORD) is False


# --- UserService -------------------------------------------------------------


@pytest.mark.unit
class TestUserService:
    async def test_create_hashes_password_and_commits_once(self) -> None:
        service, repo, uow = _build_user_service()

        view = await service.create(
            CreateUserCommand(
                email="new@example.com",
                full_name="New User",
                password=_VALID_PASSWORD,
            )
        )

        assert view.email == "new@example.com"
        assert uow.commits == 1
        stored = await repo.get_by_id(view.id)
        assert stored is not None
        assert stored.hashed_password == _HASH_PREFIX + _VALID_PASSWORD

    async def test_create_short_password_rolls_back(self) -> None:
        service, repo, uow = _build_user_service()

        with pytest.raises(ValueError):
            await service.create(
                CreateUserCommand(
                    email="bad@example.com",
                    full_name="Bad",
                    password=_SHORT_PASSWORD,
                )
            )

        assert repo.persisted == {}

    async def test_list_users_returns_total(self) -> None:
        service, repo, _ = _build_user_service()
        _seed_user(repo, email="a@example.com")
        _seed_user(repo, email="b@example.com")

        listing = await service.list_users(ListUsersQuery())

        assert listing.total == 2
        assert {item.email for item in listing.items} == {
            "a@example.com",
            "b@example.com",
        }

    async def test_get_hit_and_miss(self) -> None:
        service, repo, _ = _build_user_service()
        user = _seed_user(repo)

        assert (await service.get(GetUserQuery(user_id=user.id))) is not None
        assert (await service.get(GetUserQuery(user_id=uuid4()))) is None

    async def test_update_applies_partial_changes(self) -> None:
        service, repo, uow = _build_user_service()
        user = _seed_user(repo)

        view = await service.update(
            UpdateUserCommand(user_id=user.id, full_name="Renamed")
        )

        assert view.full_name == "Renamed"
        assert view.email == user.email  # unchanged
        assert uow.commits == 1

    async def test_update_missing_raises(self) -> None:
        service, _, _ = _build_user_service()

        with pytest.raises(UserNotFoundError):
            await service.update(UpdateUserCommand(user_id=uuid4(), full_name="X"))

    async def test_assign_role_commits(self) -> None:
        service, repo, uow = _build_user_service()
        user = _seed_user(repo, role=UserRole.EDITOR)

        view = await service.assign_role(
            AssignRoleCommand(user_id=user.id, role=UserRole.ADMIN)
        )

        assert view.role == UserRole.ADMIN.value
        assert uow.commits == 1

    async def test_change_password_verifies_current(self) -> None:
        service, repo, uow = _build_user_service()
        user = _seed_user(repo)

        await service.change_password(
            ChangePasswordCommand(
                user_id=user.id,
                current_password=_VALID_PASSWORD,
                new_password="brand-new-passphrase",
            )
        )

        assert uow.commits == 1
        stored = await service.get(GetUserQuery(user_id=user.id))
        assert stored is not None

    async def test_change_password_wrong_current_raises(self) -> None:
        service, repo, _ = _build_user_service()
        user = _seed_user(repo)

        with pytest.raises(CurrentPasswordIncorrectError):
            await service.change_password(
                ChangePasswordCommand(
                    user_id=user.id,
                    current_password="not-the-password",
                    new_password="brand-new-passphrase",
                )
            )

    async def test_delete_hit_and_miss(self) -> None:
        service, repo, _ = _build_user_service()
        user = _seed_user(repo)

        assert await service.delete(DeleteUserCommand(user_id=user.id)) is True
        assert await service.delete(DeleteUserCommand(user_id=uuid4())) is False


# --- AuthenticationService ---------------------------------------------------


@pytest.mark.unit
class TestAuthenticationService:
    async def test_login_returns_token(self) -> None:
        service, repo = _build_auth_service()
        user = _seed_user(repo, email="login@example.com")

        token_view = await service.login(
            LoginCommand(email="login@example.com", password=_VALID_PASSWORD)
        )

        assert token_view.access_token == _TOKEN_PREFIX + str(user.id)
        assert token_view.token_type == "bearer"

    async def test_login_unknown_email_raises(self) -> None:
        service, _ = _build_auth_service()

        with pytest.raises(InvalidCredentialsError):
            await service.login(
                LoginCommand(email="missing@example.com", password=_VALID_PASSWORD)
            )

    async def test_login_wrong_password_raises(self) -> None:
        service, repo = _build_auth_service()
        _seed_user(repo, email="login@example.com")

        with pytest.raises(InvalidCredentialsError):
            await service.login(
                LoginCommand(email="login@example.com", password="wrong-password")
            )

    async def test_login_inactive_user_raises(self) -> None:
        service, repo = _build_auth_service()
        _seed_user(repo, email="inactive@example.com", is_active=False)

        with pytest.raises(InactiveUserError):
            await service.login(
                LoginCommand(email="inactive@example.com", password=_VALID_PASSWORD)
            )

    async def test_validate_token_round_trip(self) -> None:
        service, repo = _build_auth_service()
        user = _seed_user(repo)

        token_view = service.issue_token(user)
        payload = service.validate_token(token_view.access_token)

        assert payload is not None
        assert payload["sub"] == str(user.id)

    async def test_validate_invalid_token_returns_none(self) -> None:
        service, _ = _build_auth_service()

        assert service.validate_token("garbage") is None
