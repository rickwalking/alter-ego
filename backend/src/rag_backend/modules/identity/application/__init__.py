"""Application layer for the identity bounded context (private to the module).

Holds the three identity use-case entry points and their collaborator ports.
Cross-module consumers do NOT import this subpackage directly — they use the
module facade (``rag_backend.modules.identity``). This ``__init__`` is an
intra-module convenience for the api/infrastructure layers.
"""

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

__all__ = [
    "AuthenticationDeps",
    "AuthenticationService",
    "CurrentPasswordIncorrectError",
    "InactiveUserError",
    "InvalidCredentialsError",
    "PasswordHasher",
    "PasswordService",
    "TokenIssuer",
    "UserNotFoundError",
    "UserService",
    "UserServiceDeps",
]
