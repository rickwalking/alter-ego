"""Typed command/query objects for the identity bounded context (private).

These are the boundary-safe inputs the identity application services accept.
Each maps onto the same operations the legacy auth/user routes and dependencies
perform today, so the extraction is behavior-preserving (AE-0098). Grouping
inputs into typed dataclasses keeps the service methods at ≤3 arguments
(backend/CLAUDE.md) without arbitrary dict bundles.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rag_backend.modules.identity.domain.models import UserRole


@dataclass(frozen=True)
class CreateUserCommand:
    """Inputs to create a user (password is hashed by the service)."""

    email: str
    full_name: str
    password: str
    role: UserRole = UserRole.EDITOR
    is_active: bool = True


@dataclass(frozen=True)
class ListUsersQuery:
    """Inputs to list a page of users."""

    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetUserQuery:
    """Inputs to fetch a single user by id."""

    user_id: UUID


@dataclass(frozen=True)
class UpdateUserCommand:
    """Inputs to update a user's mutable profile fields.

    ``None`` fields are left unchanged so partial updates mirror the legacy
    route behavior without overwriting omitted values.
    """

    user_id: UUID
    full_name: str | None = None
    email: str | None = None
    is_active: bool | None = None


@dataclass(frozen=True)
class DeleteUserCommand:
    """Inputs to delete a user by id."""

    user_id: UUID


@dataclass(frozen=True)
class AssignRoleCommand:
    """Inputs to assign a role to a user."""

    user_id: UUID
    role: UserRole


@dataclass(frozen=True)
class LoginCommand:
    """Inputs to authenticate a user by email + password."""

    email: str
    password: str


@dataclass(frozen=True)
class ChangePasswordCommand:
    """Inputs to change a user's password (verifies the current one first)."""

    user_id: UUID
    current_password: str
    new_password: str


__all__ = [
    "AssignRoleCommand",
    "ChangePasswordCommand",
    "CreateUserCommand",
    "DeleteUserCommand",
    "GetUserQuery",
    "ListUsersQuery",
    "LoginCommand",
    "UpdateUserCommand",
]
