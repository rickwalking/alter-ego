"""Public facade for the identity bounded context.

**This file is the module's public API.** Cross-module code SHALL import only
the symbols re-exported here (also re-exported from the package ``__init__``);
everything else under ``rag_backend.modules.identity.*`` is private to the
module.

The facade exposes:

* ``UserService`` / ``AuthenticationService`` / ``PasswordService`` — the three
  use-case entry points (user CRUD + role assignment, login/token issue+validate,
  hash/verify/policy);
* the typed **command/query** objects those operations accept;
* the boundary-safe **view** DTOs they return (``UserView``/``UserListView``/
  ``AccessTokenView``);
* the collaborator ports (``PasswordHasher``/``TokenIssuer``/``UserRepository``)
  and the re-exported aggregate (``User``/``UserRole``);
* the **role-check FastAPI dependencies** (``require_authenticated_user`` etc.),
  re-exported through the facade but still backed by ``api/middleware/auth.py`` at
  root (AE-0098 — not relocated);
* ``IdentityAdapters`` / ``IdentityServices`` / ``bootstrap_module`` — the
  composition root (manual constructor injection).

Consumers SHALL NOT import internals such as
``rag_backend.modules.identity.application.user_service`` or
``rag_backend.modules.identity.domain.models`` directly.
"""

from rag_backend.api.dependencies.auth import (
    get_optional_user,
    get_user_repo,
    require_admin,
    require_authenticated_user,
    require_editor_or_admin,
    require_owner_or_admin,
)
from rag_backend.modules.identity.api.views import (
    AccessTokenView,
    UserListView,
    UserView,
)
from rag_backend.modules.identity.application.admin_handlers import (
    AdminUserDeps,
    AdminUserHandler,
    CreatedUserView,
    CreateUserInput,
    DeleteUserInput,
    InvalidRoleError,
    LastAdminError,
    SelfDeleteError,
    UpdateUserInput,
    UserAlreadyExistsError,
)
from rag_backend.modules.identity.application.auth_handlers import (
    AuthCommandDeps,
    AuthCommandHandler,
)
from rag_backend.modules.identity.application.authentication_service import (
    AuthenticationDeps,
    AuthenticationService,
    InactiveUserError,
    InvalidCredentialsError,
)
from rag_backend.modules.identity.application.password_service import PasswordService
from rag_backend.modules.identity.application.ports import (
    PasswordHasher,
    TokenIssuer,
)
from rag_backend.modules.identity.application.user_service import (
    CurrentPasswordIncorrectError,
    UserNotFoundError,
    UserService,
    UserServiceDeps,
)
from rag_backend.modules.identity.bootstrap import (
    IdentityAdapters,
    IdentityServices,
    bootstrap_module,
)
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
    "AccessTokenView",
    "AdminUserDeps",
    "AdminUserHandler",
    "AssignRoleCommand",
    "AuthCommandDeps",
    "AuthCommandHandler",
    "AuthenticationDeps",
    "AuthenticationService",
    "ChangePasswordCommand",
    "CreateUserCommand",
    "CreateUserInput",
    "CreatedUserView",
    "CurrentPasswordIncorrectError",
    "DeleteUserCommand",
    "DeleteUserInput",
    "GetUserQuery",
    "IdentityAdapters",
    "IdentityServices",
    "InactiveUserError",
    "InvalidCredentialsError",
    "InvalidRoleError",
    "LastAdminError",
    "ListUsersQuery",
    "LoginCommand",
    "PasswordHasher",
    "PasswordService",
    "SelfDeleteError",
    "TokenIssuer",
    "UpdateUserCommand",
    "UpdateUserInput",
    "User",
    "UserAlreadyExistsError",
    "UserListView",
    "UserNotFoundError",
    "UserRepository",
    "UserRole",
    "UserService",
    "UserServiceDeps",
    "UserView",
    "bootstrap_module",
    "get_optional_user",
    "get_user_repo",
    "require_admin",
    "require_authenticated_user",
    "require_editor_or_admin",
    "require_owner_or_admin",
]
