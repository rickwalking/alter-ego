"""Unit tests for the last-active-admin guard of :class:`AdminUserHandler.update`.

Scenarios: ``tests/features/last_active_admin_guard_ae0585.feature``. The fakes
and builders are the identity handler test doubles, whose repository only
persists on a Unit of Work commit, so a refused update that never commits is
observable.
"""

from __future__ import annotations

import pytest

from rag_backend.modules.identity import (
    LastActiveAdminDeactivationError,
    LastAdminError,
    UpdateUserInput,
    UserRole,
)
from tests.unit.modules.identity.test_identity_handlers import (
    _build_admin_handler,
    _seed_user,
)

_ADMIN_EMAIL = "admin@example.com"
_OTHER_ADMIN_EMAIL = "other-admin@example.com"
_EDITOR_EMAIL = "editor@example.com"
_EDITOR = UserRole.EDITOR.value
_ADMIN = UserRole.ADMIN.value


@pytest.mark.unit
class TestLastActiveAdminGuard:
    """``AdminUserHandler.update`` never leaves the app without an active admin."""

    # Scenario: Deactivating the last active admin is refused
    async def test_deactivating_the_last_active_admin_is_refused(self) -> None:
        handler, repo, uow = _build_admin_handler()
        admin = _seed_user(repo, email=_ADMIN_EMAIL, role=UserRole.ADMIN)

        with pytest.raises(LastActiveAdminDeactivationError):
            await handler.update(UpdateUserInput(user_id=admin.id, is_active=False))

        assert uow.commits == 0
        stored = await repo.get_by_id(admin.id)
        assert stored is not None
        assert stored.is_active is True

    # Scenario: Deactivating the last active admin is refused
    async def test_the_deactivation_refusal_is_a_last_admin_error(self) -> None:
        handler, repo, _ = _build_admin_handler()
        admin = _seed_user(repo, email=_ADMIN_EMAIL, role=UserRole.ADMIN)
        _seed_user(repo, email=_OTHER_ADMIN_EMAIL, role=UserRole.ADMIN, is_active=False)

        with pytest.raises(LastAdminError):
            await handler.update(UpdateUserInput(user_id=admin.id, is_active=False))

    # Scenario: Demoting the last active admin is refused when the other admins
    # are inactive
    async def test_demoting_with_only_inactive_other_admins_is_refused(
        self,
    ) -> None:
        handler, repo, uow = _build_admin_handler()
        admin = _seed_user(repo, email=_ADMIN_EMAIL, role=UserRole.ADMIN)
        _seed_user(repo, email=_OTHER_ADMIN_EMAIL, role=UserRole.ADMIN, is_active=False)

        with pytest.raises(LastAdminError) as caught:
            await handler.update(UpdateUserInput(user_id=admin.id, role=_EDITOR))

        assert not isinstance(caught.value, LastActiveAdminDeactivationError)
        assert uow.commits == 0
        stored = await repo.get_by_id(admin.id)
        assert stored is not None
        assert stored.role == UserRole.ADMIN

    # Scenario: Demoting and deactivating in one request is refused as a demotion
    async def test_demote_and_deactivate_is_refused_as_a_demotion(self) -> None:
        handler, repo, uow = _build_admin_handler()
        admin = _seed_user(repo, email=_ADMIN_EMAIL, role=UserRole.ADMIN)

        with pytest.raises(LastAdminError) as caught:
            await handler.update(
                UpdateUserInput(user_id=admin.id, role=_EDITOR, is_active=False)
            )

        assert not isinstance(caught.value, LastActiveAdminDeactivationError)
        assert uow.commits == 0
        stored = await repo.get_by_id(admin.id)
        assert stored is not None
        assert stored.role == UserRole.ADMIN
        assert stored.is_active is True

    # Scenario: With two active admins one can be deactivated
    async def test_deactivating_with_another_active_admin_is_allowed(self) -> None:
        handler, repo, uow = _build_admin_handler()
        admin = _seed_user(repo, email=_ADMIN_EMAIL, role=UserRole.ADMIN)
        _seed_user(repo, email=_OTHER_ADMIN_EMAIL, role=UserRole.ADMIN)

        view = await handler.update(UpdateUserInput(user_id=admin.id, is_active=False))

        assert view.is_active is False
        assert uow.commits == 1

    # Scenario: With two active admins one can be demoted
    async def test_demoting_with_another_active_admin_is_allowed(self) -> None:
        handler, repo, uow = _build_admin_handler()
        admin = _seed_user(repo, email=_ADMIN_EMAIL, role=UserRole.ADMIN)
        _seed_user(repo, email=_OTHER_ADMIN_EMAIL, role=UserRole.ADMIN)

        view = await handler.update(UpdateUserInput(user_id=admin.id, role=_EDITOR))

        assert view.role == _EDITOR
        assert uow.commits == 1

    # Scenario: An inactive admin can be demoted while one active admin remains
    async def test_an_inactive_admin_can_be_demoted(self) -> None:
        handler, repo, _ = _build_admin_handler()
        _seed_user(repo, email=_ADMIN_EMAIL, role=UserRole.ADMIN)
        inactive = _seed_user(
            repo, email=_OTHER_ADMIN_EMAIL, role=UserRole.ADMIN, is_active=False
        )

        view = await handler.update(UpdateUserInput(user_id=inactive.id, role=_EDITOR))

        assert view.role == _EDITOR

    # Scenario: Editors and other changes are not affected by the guard
    async def test_an_editor_can_be_deactivated(self) -> None:
        handler, repo, _ = _build_admin_handler()
        _seed_user(repo, email=_ADMIN_EMAIL, role=UserRole.ADMIN)
        editor = _seed_user(repo, email=_EDITOR_EMAIL)

        view = await handler.update(UpdateUserInput(user_id=editor.id, is_active=False))

        assert view.is_active is False

    # Scenario: Editors and other changes are not affected by the guard
    async def test_keeping_the_last_admin_active_and_admin_is_allowed(self) -> None:
        handler, repo, uow = _build_admin_handler()
        admin = _seed_user(repo, email=_ADMIN_EMAIL, role=UserRole.ADMIN)

        view = await handler.update(
            UpdateUserInput(user_id=admin.id, role=_ADMIN, is_active=True)
        )

        assert view.role == _ADMIN
        assert view.is_active is True
        assert uow.commits == 1
