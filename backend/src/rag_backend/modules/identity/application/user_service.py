"""User management use cases for the identity bounded context (private).

The public facade re-exports this under ``UserService``; cross-module code never
imports this path directly.

This is a **behavior-preserving** facade over the existing user repository
(AE-0098): each method maps a typed command/query onto the same persistence
calls the legacy admin/auth routes make today. Write use cases run under the
injected request-scoped Unit of Work, which is the **single commit owner**
(ADR-0009 §9): the repository only flushes, and this service commits once via
the UoW at the end of a successful write, or rolls back with no partial writes
if it raises. Read use cases do not commit.

Dependencies are injected through the constructor (manual constructor
injection); this service does not resolve a global container.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rag_backend.modules.identity.api.views import UserListView, UserView
from rag_backend.modules.identity.application.password_service import PasswordService
from rag_backend.modules.identity.constants import (
    ERR_CURRENT_CREDENTIAL_INCORRECT,
    ERR_USER_NOT_FOUND,
)
from rag_backend.modules.identity.domain.commands import (
    AssignRoleCommand,
    ChangePasswordCommand,
    CreateUserCommand,
    DeleteUserCommand,
    GetUserQuery,
    ListUsersQuery,
    UpdateUserCommand,
)
from rag_backend.modules.identity.domain.models import User
from rag_backend.modules.identity.domain.ports import UserRepository
from rag_backend.platform.database import UnitOfWork


class UserNotFoundError(Exception):
    """Raised when a referenced user does not exist."""


class CurrentPasswordIncorrectError(Exception):
    """Raised when a password change supplies the wrong current password."""


@dataclass(frozen=True)
class UserServiceDeps:
    """Collaborators grouped to keep the constructor at ≤3 arguments.

    Bundles the password service and the request-scoped Unit of Work so the
    user repository stays explicit while the constructor honours the
    backend/CLAUDE.md 3-argument limit.
    """

    passwords: PasswordService
    unit_of_work: UnitOfWork


class UserService:
    """Use-case entry point for user CRUD + role assignment (identity)."""

    def __init__(
        self,
        repository: UserRepository,
        deps: UserServiceDeps,
    ) -> None:
        self._repository = repository
        self._passwords = deps.passwords
        self._unit_of_work = deps.unit_of_work

    async def create(self, command: CreateUserCommand) -> UserView:
        """Create a user with a hashed password (committed once)."""
        user = User(
            email=command.email,
            full_name=command.full_name,
            hashed_password=self._passwords.hash(command.password),
            role=command.role,
            is_active=command.is_active,
        )
        async with self._unit_of_work:
            created = await self._repository.create(user)
            view = self._to_view(created)
        return view

    async def list_users(self, query: ListUsersQuery) -> UserListView:
        """List a page of users plus the matching total.

        Named ``list_users`` (not ``list``) to avoid shadowing the builtin
        ``list`` used in return annotations elsewhere on this class.
        """
        users = await self._repository.get_all(limit=query.limit, offset=query.offset)
        total = await self._repository.count()
        return UserListView(items=[self._to_view(user) for user in users], total=total)

    async def get(self, query: GetUserQuery) -> UserView | None:
        """Fetch a single user by id, or ``None`` if absent."""
        user = await self._repository.get_by_id(query.user_id)
        if user is None:
            return None
        return self._to_view(user)

    async def update(self, command: UpdateUserCommand) -> UserView:
        """Apply partial profile changes to a user (committed once)."""
        async with self._unit_of_work:
            user = await self._require_user(command.user_id)
            self._apply_updates(user, command)
            updated = await self._repository.update(user)
            view = self._to_view(updated)
        return view

    async def assign_role(self, command: AssignRoleCommand) -> UserView:
        """Assign a role to a user (committed once)."""
        async with self._unit_of_work:
            user = await self._require_user(command.user_id)
            user.set_role(command.role)
            updated = await self._repository.update(user)
            view = self._to_view(updated)
        return view

    async def change_password(self, command: ChangePasswordCommand) -> None:
        """Change a user's password after verifying the current one (committed once)."""
        async with self._unit_of_work:
            user = await self._require_user(command.user_id)
            if not self._passwords.verify(
                command.current_password, user.hashed_password
            ):
                raise CurrentPasswordIncorrectError(ERR_CURRENT_CREDENTIAL_INCORRECT)
            user.hashed_password = self._passwords.hash(command.new_password)
            await self._repository.update(user)

    async def delete(self, command: DeleteUserCommand) -> bool:
        """Delete a user by id (committed once); ``False`` if absent."""
        async with self._unit_of_work:
            deleted = await self._repository.delete(command.user_id)
        return deleted

    async def _require_user(self, user_id: UUID) -> User:
        user = await self._repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(ERR_USER_NOT_FOUND)
        return user

    @staticmethod
    def _apply_updates(user: User, command: UpdateUserCommand) -> None:
        if command.full_name is not None:
            user.full_name = command.full_name
        if command.email is not None:
            user.email = command.email
        if command.is_active is not None:
            user.is_active = command.is_active

    @staticmethod
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
    "CurrentPasswordIncorrectError",
    "UserNotFoundError",
    "UserService",
    "UserServiceDeps",
]
