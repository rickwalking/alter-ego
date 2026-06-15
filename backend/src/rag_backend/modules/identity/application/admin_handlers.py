"""Admin command/query handlers for the identity bounded context (private).

The public facade re-exports :class:`AdminUserHandler` and its command/view
types; cross-module code and the inbound HTTP adapters never import this path
directly.

This is a **behavior-preserving** orchestration layer (AE-0099) over the user
repository and bcrypt password port. Each handler maps a typed admin command
onto the exact persistence calls the legacy ``/api/admin/users`` routes make
today, so the wire behavior (status codes, response shapes, last-admin / self
guards, temp-password generation) stays byte-identical when the routes move
behind the facade.

Writes run inside the request-scoped Unit of Work — the single commit owner
(ADR-0009 §9): the repository only flushes, and the handler commits once on a
clean exit or rolls back with no partial writes on failure. Role mutations use
the aggregate's ``set_role``/``activate``/``deactivate`` (which bump
``updated_at``) exactly like the legacy route, preserving its snapshotted 200
contract (and avoiding the unrelated change-password update path).

Domain decisions (conflict / invalid role / last-admin / self-delete) raise
typed errors; the inbound adapter maps each to the legacy HTTP status + message
so no HTTP framework leaks into the module.
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from uuid import UUID

from rag_backend.modules.identity.api.views import UserListView, UserView
from rag_backend.modules.identity.application.password_service import PasswordService
from rag_backend.modules.identity.application.user_service import UserNotFoundError
from rag_backend.modules.identity.constants import (
    ERR_INVALID_ROLE,
    ERR_LAST_ADMIN,
    ERR_SELF_DELETE,
    ERR_USER_ALREADY_EXISTS,
    ERR_USER_NOT_FOUND,
    GENERATED_CREDENTIAL_LENGTH,
    GENERATED_SPECIAL_CHARS,
)
from rag_backend.modules.identity.domain.models import User, UserRole
from rag_backend.modules.identity.domain.ports import UserRepository
from rag_backend.platform.database import UnitOfWork

# Listing cap that mirrors the legacy admin route's ``get_all(limit=1000)`` so
# the page size (and therefore the snapshotted ordering/total) is unchanged.
_ADMIN_LIST_LIMIT = 1000


class UserAlreadyExistsError(Exception):
    """Raised when creating a user whose email is already taken."""


class InvalidRoleError(Exception):
    """Raised when a supplied role string is not a known role.

    Carries the offending ``role`` so the inbound adapter can format the exact
    legacy 422 message without the module knowing about HTTP.
    """

    def __init__(self, role: str) -> None:
        super().__init__(ERR_INVALID_ROLE)
        self.role = role


class LastAdminError(Exception):
    """Raised when an operation would demote or delete the last admin."""


class SelfDeleteError(Exception):
    """Raised when an admin attempts to delete their own account."""


@dataclass(frozen=True)
class CreateUserInput:
    """Inputs to the admin create-user use case (role is a raw string)."""

    email: str
    full_name: str
    role: str
    password: str | None = None


@dataclass(frozen=True)
class UpdateUserInput:
    """Inputs to the admin update-user use case (role/active are optional)."""

    user_id: UUID
    role: str | None = None
    is_active: bool | None = None


@dataclass(frozen=True)
class DeleteUserInput:
    """Inputs to the admin delete-user use case (guards against self/last)."""

    user_id: UUID
    requested_by: UUID


@dataclass(frozen=True)
class CreatedUserView:
    """Boundary-safe result of admin create (id + email + optional temp pass)."""

    id: UUID
    email: str
    temp_password: str | None


@dataclass(frozen=True)
class AdminUserDeps:
    """Collaborators grouped to keep the handler constructor at ≤3 arguments."""

    passwords: PasswordService
    unit_of_work: UnitOfWork


class AdminUserHandler:
    """Handle the ``/api/admin/users`` CRUD + reset-password use cases."""

    def __init__(
        self,
        repository: UserRepository,
        deps: AdminUserDeps,
    ) -> None:
        self._repository = repository
        self._passwords = deps.passwords
        self._unit_of_work = deps.unit_of_work

    async def list_users(self) -> UserListView:
        """List users (capped at the legacy 1000) plus the matching total."""
        users = await self._repository.get_all(limit=_ADMIN_LIST_LIMIT)
        total = await self._repository.count()
        return UserListView(
            items=[_to_view(user) for user in users],
            total=total,
        )

    async def create(self, command: CreateUserInput) -> CreatedUserView:
        """Create a user (auto-generating a temp password when none given)."""
        role = _parse_role(command.role)
        temp_password, password = self._resolve_password(command.password)
        async with self._unit_of_work:
            await self._reject_existing_email(command.email)
            user = User(
                email=command.email,
                full_name=command.full_name,
                hashed_password=self._passwords.hash(password),
                role=role,
                is_active=True,
            )
            created = await self._repository.create(user)
            result = CreatedUserView(
                id=created.id, email=created.email, temp_password=temp_password
            )
        return result

    async def update(self, command: UpdateUserInput) -> UserView:
        """Apply role/active changes (with the last-admin guard) and commit once.

        Mirrors the legacy route ordering: the user is required (404) before the
        role is validated (422), so a missing user always yields 404 regardless
        of the supplied role.
        """
        async with self._unit_of_work:
            user = await self._require_user(command.user_id)
            if command.role is not None:
                await self._apply_role(user, _parse_role(command.role))
            if command.is_active is not None:
                _apply_active(user, is_active=command.is_active)
            updated = await self._repository.update(user)
            view = _to_view(updated)
        return view

    async def delete(self, command: DeleteUserInput) -> None:
        """Delete a user, guarding self-deletion and the last-admin rule."""
        if command.user_id == command.requested_by:
            raise SelfDeleteError(ERR_SELF_DELETE)
        async with self._unit_of_work:
            user = await self._require_user(command.user_id)
            await self._reject_last_admin_removal(user)
            await self._repository.delete(command.user_id)

    async def reset_password(self, user_id: UUID) -> str:
        """Reset a user's password to a fresh temp password; return it.

        Mirrors the legacy route's update path verbatim (set ``hashed_password``
        then ``repository.update``), so its snapshotted contract is preserved.
        """
        async with self._unit_of_work:
            user = await self._require_user(user_id)
            temp_password = _generate_secure_password()
            user.hashed_password = self._passwords.hash(temp_password)
            await self._repository.update(user)
        return temp_password

    async def _apply_role(self, user: User, new_role: UserRole) -> None:
        if user.role == UserRole.ADMIN and new_role != UserRole.ADMIN:
            await self._reject_demoting_last_admin()
        user.set_role(new_role)

    async def _reject_demoting_last_admin(self) -> None:
        if await self._repository.count_by_role(UserRole.ADMIN) <= 1:
            raise LastAdminError(ERR_LAST_ADMIN)

    async def _reject_last_admin_removal(self, user: User) -> None:
        if user.role != UserRole.ADMIN:
            return
        if await self._repository.count_by_role(UserRole.ADMIN) <= 1:
            raise LastAdminError(ERR_LAST_ADMIN)

    async def _reject_existing_email(self, email: str) -> None:
        if await self._repository.get_by_email(email) is not None:
            raise UserAlreadyExistsError(ERR_USER_ALREADY_EXISTS)

    async def _require_user(self, user_id: UUID) -> User:
        user = await self._repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(ERR_USER_NOT_FOUND)
        return user

    @staticmethod
    def _resolve_password(password: str | None) -> tuple[str | None, str]:
        if password:
            return None, password
        generated = _generate_secure_password()
        return generated, generated


def _apply_active(user: User, *, is_active: bool) -> None:
    """Toggle the user via the aggregate mutators (which bump ``updated_at``)."""
    if is_active:
        user.activate()
        return
    user.deactivate()


def _parse_role(role: str) -> UserRole:
    """Map a role string to the enum, raising :class:`InvalidRoleError` if unknown."""
    try:
        return UserRole(role)
    except ValueError:
        raise InvalidRoleError(role) from None


def _generate_secure_password(length: int = GENERATED_CREDENTIAL_LENGTH) -> str:
    """Generate a cryptographically secure password with mixed character classes.

    Mirrors the legacy admin route generator exactly: at least one uppercase,
    one lowercase, one digit, and one special character.
    """
    alphabet = string.ascii_letters + string.digits + GENERATED_SPECIAL_CHARS
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in GENERATED_SPECIAL_CHARS for c in password)
        ):
            return password


def _to_view(user: User) -> UserView:
    return UserView(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


__all__ = [
    "AdminUserDeps",
    "AdminUserHandler",
    "CreateUserInput",
    "CreatedUserView",
    "DeleteUserInput",
    "InvalidRoleError",
    "LastAdminError",
    "SelfDeleteError",
    "UpdateUserInput",
    "UserAlreadyExistsError",
]
