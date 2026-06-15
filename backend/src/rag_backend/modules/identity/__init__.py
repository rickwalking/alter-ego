"""Identity bounded context (Generic) — AE-0098 Phase 3 skeleton.

The identity context owns user accounts, authentication (login + JWT
issue/validate), and the password policy. This package follows the module
conventions (``docs/architecture/module-conventions.md``, AE-0081) and ADR-0009
(Domain Modular Monolith):

* per-module internal layers — ``domain/``, ``application/``,
  ``infrastructure/``, ``api/``;
* the **public-facade rule** — cross-module code imports ONLY from this
  package's public API (``public.py``, re-exported here);
* manual constructor injection via ``bootstrap_module`` (ADR-0009 §9);
* the Unit-of-Work boundary owned at the application layer.

Phase 3 is **behavior-preserving** (AE-0098): the ``UserRepository`` port and
the ``User``/``UserRole`` aggregate are *re-exported* from their legacy
locations (no physical move), JWT/bcrypt stay in ``infrastructure.auth``
(delegated, never reimplemented), and the role-check dependencies stay backed by
``api/middleware/auth.py`` (re-exported through this facade). Routes move behind
this facade in AE-0099.

Cross-module consumers SHALL import from the facade only, e.g.::

    from rag_backend.modules.identity import UserService, LoginCommand
"""

from rag_backend.modules.identity.public import (
    AccessTokenView,
    AssignRoleCommand,
    AuthenticationDeps,
    AuthenticationService,
    ChangePasswordCommand,
    CreateUserCommand,
    CurrentPasswordIncorrectError,
    DeleteUserCommand,
    GetUserQuery,
    IdentityAdapters,
    IdentityServices,
    InactiveUserError,
    InvalidCredentialsError,
    ListUsersQuery,
    LoginCommand,
    PasswordHasher,
    PasswordService,
    TokenIssuer,
    UpdateUserCommand,
    User,
    UserListView,
    UserNotFoundError,
    UserRepository,
    UserRole,
    UserService,
    UserServiceDeps,
    UserView,
    bootstrap_module,
    get_optional_user,
    get_user_repo,
    require_admin,
    require_authenticated_user,
    require_editor_or_admin,
    require_owner_or_admin,
)

__all__ = [
    "AccessTokenView",
    "AssignRoleCommand",
    "AuthenticationDeps",
    "AuthenticationService",
    "ChangePasswordCommand",
    "CreateUserCommand",
    "CurrentPasswordIncorrectError",
    "DeleteUserCommand",
    "GetUserQuery",
    "IdentityAdapters",
    "IdentityServices",
    "InactiveUserError",
    "InvalidCredentialsError",
    "ListUsersQuery",
    "LoginCommand",
    "PasswordHasher",
    "PasswordService",
    "TokenIssuer",
    "UpdateUserCommand",
    "User",
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
