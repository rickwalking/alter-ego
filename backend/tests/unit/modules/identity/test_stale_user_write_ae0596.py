"""Unit tests for the changed-fields tracking and the locked user writes.

Scenarios: ``tests/features/stale_user_write_ae0596.feature``. The handler and
service fakes are the identity test doubles, whose repository only persists on
a Unit of Work commit and records every locked read.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

import pytest

from rag_backend.domain.models import User, UserField, UserRole
from rag_backend.infrastructure.database.models import UserModel
from rag_backend.modules.identity import (
    AdminUserDeps,
    AdminUserHandler,
    AssignRoleCommand,
    ChangePasswordCommand,
    CurrentPasswordIncorrectError,
    LastAdminError,
    PasswordService,
    UpdateUserCommand,
    UpdateUserInput,
)
from tests.unit.modules.identity.test_identity_handlers import (
    _build_admin_handler,
    _build_auth_handler,
    _FakePasswordHasher,
    _FakeUserRepository,
    _SpyUnitOfWork,
)
from tests.unit.modules.identity.test_identity_handlers import (
    _seed_user as _seed_handler_user,
)
from tests.unit.modules.identity.test_identity_services import (
    _build_user_service,
)
from tests.unit.modules.identity.test_identity_services import (
    _seed_user as _seed_service_user,
)

_COUNTED = "count"
_LOCKED = "lock"
_PROFILE_FIELDS = {UserField.FULL_NAME, UserField.UPDATED_AT}

pytestmark = pytest.mark.unit


def _user() -> User:
    return User(email="track@example.com", full_name="Track", hashed_password="h")


class _OrderedRepository(_FakeUserRepository):
    """Records whether the admin count or the user lock ran first."""

    def __init__(self) -> None:
        super().__init__()
        self.order: list[str] = []

    async def get_by_id_for_update(self, user_id: UUID) -> User | None:
        self.order.append(_LOCKED)
        return await super().get_by_id_for_update(user_id)

    async def count_active_by_role(self, role: UserRole) -> int:
        self.order.append(_COUNTED)
        return await super().count_active_by_role(role)


def _ordered_admin_handler() -> tuple[
    AdminUserHandler, _OrderedRepository, _SpyUnitOfWork
]:
    repo = _OrderedRepository()
    uow = _SpyUnitOfWork(repo)
    handler = AdminUserHandler(
        repository=repo,
        deps=AdminUserDeps(
            passwords=PasswordService(hasher=_FakePasswordHasher()), unit_of_work=uow
        ),
    )
    return handler, repo, uow


# Scenario: A fresh user has no changed fields
def test_a_built_or_loaded_user_has_no_changed_fields() -> None:
    user = _user()

    loaded = UserModel.from_entity(user).to_entity()

    assert user.changed_fields() == frozenset()
    assert loaded.changed_fields() == frozenset()


# Scenario: Every assigned persisted field is reported changed
@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        (lambda u: u.rename("New"), _PROFILE_FIELDS),
        (
            lambda u: u.change_email("n@example.com"),
            {UserField.EMAIL, UserField.UPDATED_AT},
        ),
        (lambda u: u.deactivate(), {UserField.IS_ACTIVE, UserField.UPDATED_AT}),
        (lambda u: u.activate(), {UserField.IS_ACTIVE, UserField.UPDATED_AT}),
        (lambda u: u.set_role(UserRole.ADMIN), {UserField.ROLE, UserField.UPDATED_AT}),
        (
            lambda u: u.change_password("n"),
            {
                UserField.CREDENTIAL_HASH,
                UserField.CREDENTIAL_CHANGE_REQUIRED,
                UserField.SESSION_VERSION,
            },
        ),
        (
            lambda u: u.reset_password("t"),
            {
                UserField.CREDENTIAL_HASH,
                UserField.CREDENTIAL_CHANGE_REQUIRED,
                UserField.SESSION_VERSION,
            },
        ),
    ],
)
def test_each_operation_reports_exactly_its_fields(
    operation: Callable[[User], None], expected: set[UserField]
) -> None:
    user = _user()

    operation(user)

    assert user.changed_fields() == frozenset(expected)


# Scenario: Every assigned persisted field is reported changed
def test_direct_assignments_are_tracked_but_never_the_id() -> None:
    user = _user()

    user.token_version = 4
    user.id = user.id
    user.created_at = user.created_at

    assert user.changed_fields() == frozenset({UserField.SESSION_VERSION})


# Scenario: An admin edit reads the user locked inside the unit of work
async def test_an_admin_rename_reads_locked_and_saves_only_the_name() -> None:
    handler, repo, uow = _build_admin_handler()
    user = _seed_handler_user(repo)

    await handler.update(UpdateUserInput(user_id=user.id, full_name="New Name"))

    assert repo.locked == [user.id]
    assert uow.commits == 1
    stored = await repo.get_by_id(user.id)
    assert stored is not None
    assert stored.changed_fields() == frozenset(_PROFILE_FIELDS)


# Scenario: An admin edit reads the user locked inside the unit of work
@pytest.mark.parametrize(
    "edit",
    [
        lambda user_id: UpdateUserInput(user_id=user_id, role=UserRole.EDITOR.value),
        lambda user_id: UpdateUserInput(user_id=user_id, is_active=False),
    ],
)
async def test_a_role_or_state_edit_counts_admins_before_the_user_lock(
    edit: Callable[[UUID], UpdateUserInput],
) -> None:
    handler, repo, uow = _ordered_admin_handler()
    _seed_handler_user(repo, email="a1@example.com", role=UserRole.ADMIN)
    target = _seed_handler_user(repo, email="a2@example.com", role=UserRole.ADMIN)

    await handler.update(edit(target.id))

    assert repo.order == [_COUNTED, _LOCKED]
    assert uow.commits == 1


# Scenario: An admin edit reads the user locked inside the unit of work
async def test_a_rename_locks_no_admin_rows() -> None:
    handler, repo, _ = _ordered_admin_handler()
    admin = _seed_handler_user(repo, role=UserRole.ADMIN)

    await handler.update(UpdateUserInput(user_id=admin.id, full_name="Renamed"))

    assert repo.order == [_LOCKED]


# Scenario: A refused admin edit commits nothing
async def test_deactivating_the_last_admin_is_refused_on_the_locked_user() -> None:
    handler, repo, uow = _build_admin_handler()
    admin = _seed_handler_user(repo, role=UserRole.ADMIN)

    with pytest.raises(LastAdminError):
        await handler.update(UpdateUserInput(user_id=admin.id, is_active=False))

    assert repo.locked == [admin.id]
    assert (uow.commits, uow.rollbacks) == (0, 1)
    stored = await repo.get_by_id(admin.id)
    assert stored is not None
    assert stored.is_active is True


# Scenario: A user service edit reads the user locked inside the unit of work
async def test_the_service_update_reads_locked_and_uses_the_mutators() -> None:
    service, repo, uow = _build_user_service()
    user = _seed_service_user(repo)

    await service.update(
        UpdateUserCommand(user_id=user.id, email="moved@example.com", is_active=False)
    )

    assert repo.locked == [user.id]
    assert uow.commits == 1
    stored = await repo.get_by_id(user.id)
    assert stored is not None
    assert stored.changed_fields() == frozenset({
        UserField.EMAIL,
        UserField.IS_ACTIVE,
        UserField.UPDATED_AT,
    })


# Scenario: A user service edit reads the user locked inside the unit of work
async def test_the_service_reactivation_and_role_read_locked() -> None:
    service, repo, uow = _build_user_service()
    user = _seed_service_user(repo, is_active=False)

    await service.update(UpdateUserCommand(user_id=user.id, is_active=True))
    await service.assign_role(AssignRoleCommand(user_id=user.id, role=UserRole.ADMIN))

    assert repo.locked == [user.id, user.id]
    assert uow.commits == 2
    stored = await repo.get_by_id(user.id)
    assert stored is not None
    assert (stored.is_active, stored.role) == (True, UserRole.ADMIN)


# Scenario: A password change reads the user locked inside the unit of work
async def test_a_refused_password_change_rolls_back_the_locked_read() -> None:
    handler, repo, uow = _build_auth_handler()
    user = _seed_handler_user(repo)

    with pytest.raises(CurrentPasswordIncorrectError):
        await handler.change_password(
            ChangePasswordCommand(
                user_id=user.id, current_password="wrong", new_password="whatever-new"
            )
        )

    assert repo.locked == [user.id]
    assert (uow.commits, uow.rollbacks) == (0, 1)
