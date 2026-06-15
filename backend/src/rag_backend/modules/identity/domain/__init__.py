"""Domain layer for the identity bounded context (private to the module).

Exposes the identity aggregate (``User``), its role value object
(``UserRole``), the ``UserRepository`` port, and the typed command/query
objects. Cross-module consumers do NOT import this subpackage directly — they
use the module facade (``rag_backend.modules.identity``). This ``__init__`` is
an intra-module convenience for the application/infrastructure/api layers.
"""

from rag_backend.modules.identity.domain.commands import (
    AssignRoleCommand,
    ChangePasswordCommand,
    CreateUserCommand,
    DeleteUserCommand,
    GetUserQuery,
    ListUsersQuery,
    LoginCommand,
    UpdateUserCommand,
)
from rag_backend.modules.identity.domain.models import User, UserRole
from rag_backend.modules.identity.domain.ports import UserRepository

__all__ = [
    "AssignRoleCommand",
    "ChangePasswordCommand",
    "CreateUserCommand",
    "DeleteUserCommand",
    "GetUserQuery",
    "ListUsersQuery",
    "LoginCommand",
    "UpdateUserCommand",
    "User",
    "UserRepository",
    "UserRole",
]
