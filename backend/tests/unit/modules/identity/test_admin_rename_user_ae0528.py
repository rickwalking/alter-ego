"""Unit tests for the admin rename-user path of :class:`AdminUserHandler`.

Scenarios: ``tests/features/admin_edit_user_name_ae0528.feature``. The fakes and
builders are the identity handler test doubles, whose repository only persists on
a Unit of Work commit, so a rolled-back rename is observable.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from rag_backend.modules.identity import (
    LastAdminError,
    UpdateUserInput,
    UserNotFoundError,
    UserRole,
)
from tests.unit.modules.identity.test_identity_handlers import (
    _build_admin_handler,
    _seed_user,
)

_OLD_NAME = "Test User"
_NEW_NAME = "John Smith"


@pytest.mark.unit
class TestAdminRenameUser:
    """``AdminUserHandler.update`` with a ``full_name``."""

    # Scenario: Admin renames a user
    async def test_rename_sets_the_name_and_bumps_updated_at(self) -> None:
        handler, repo, uow = _build_admin_handler()
        user = _seed_user(repo)
        before = user.updated_at

        view = await handler.update(
            UpdateUserInput(user_id=user.id, full_name=_NEW_NAME)
        )

        assert view.full_name == _NEW_NAME
        assert uow.commits == 1
        stored = await repo.get_by_id(user.id)
        assert stored is not None
        assert stored.full_name == _NEW_NAME
        assert stored.updated_at > before

    # Scenario: Admin renames a user
    async def test_rename_with_role_and_active_applies_all(self) -> None:
        handler, repo, _ = _build_admin_handler()
        user = _seed_user(repo, role=UserRole.EDITOR, is_active=True)

        view = await handler.update(
            UpdateUserInput(
                user_id=user.id, role="admin", is_active=False, full_name=_NEW_NAME
            )
        )

        assert view.full_name == _NEW_NAME
        assert view.role == UserRole.ADMIN.value
        assert view.is_active is False

    # Scenario: Omitting the name leaves it unchanged
    async def test_omitted_name_keeps_the_stored_name(self) -> None:
        handler, repo, _ = _build_admin_handler()
        user = _seed_user(repo)

        view = await handler.update(UpdateUserInput(user_id=user.id, role="admin"))

        assert view.full_name == _OLD_NAME

    # Scenario: Renaming an unknown user returns 404
    async def test_rename_unknown_user_raises_not_found(self) -> None:
        handler, _, uow = _build_admin_handler()

        with pytest.raises(UserNotFoundError):
            await handler.update(UpdateUserInput(user_id=uuid4(), full_name=_NEW_NAME))

        assert uow.commits == 0

    # Scenario: The last-admin rule still holds when the name is edited with the role
    async def test_rename_with_last_admin_demotion_is_rejected(self) -> None:
        handler, repo, uow = _build_admin_handler()
        admin = _seed_user(repo, email="admin@example.com", role=UserRole.ADMIN)

        with pytest.raises(LastAdminError):
            await handler.update(
                UpdateUserInput(user_id=admin.id, role="editor", full_name=_NEW_NAME)
            )

        assert uow.rollbacks == 1
        stored = await repo.get_by_id(admin.id)
        assert stored is not None
        assert stored.full_name == _OLD_NAME
        assert stored.role == UserRole.ADMIN
