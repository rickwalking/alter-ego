"""Authentication use cases for the identity bounded context (private).

The public facade re-exports this under ``AuthenticationService``; cross-module
code never imports this path directly.

This is a **behavior-preserving** facade over the existing login + JWT helpers
(AE-0098): credential checking reuses the password port and the user
repository; token issue/validate delegate to the injected
:class:`~rag_backend.modules.identity.application.ports.TokenIssuer`, which
wraps the UNCHANGED ``infrastructure.auth`` functions. The HS256 payload,
algorithm, and expiry stay byte-identical because the same functions run.

Dependencies are injected through the constructor (manual constructor injection,
ADR-0009 §9). This service does not resolve a global container.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules.identity.api.views import AccessTokenView
from rag_backend.modules.identity.application.password_service import PasswordService
from rag_backend.modules.identity.application.ports import TokenIssuer
from rag_backend.modules.identity.constants import (
    ERR_INVALID_CREDENTIALS,
    ERR_USER_INACTIVE,
)
from rag_backend.modules.identity.domain.commands import LoginCommand
from rag_backend.modules.identity.domain.models import User
from rag_backend.modules.identity.domain.ports import UserRepository


class InvalidCredentialsError(Exception):
    """Raised when an email/password pair does not authenticate."""


class InactiveUserError(Exception):
    """Raised when an otherwise-valid user account is deactivated."""


@dataclass(frozen=True)
class AuthenticationDeps:
    """Collaborators grouped to keep the constructor at ≤3 arguments.

    Bundles the password service and the token issuer so the user repository
    stays explicit while the constructor honours the backend/CLAUDE.md
    3-argument limit.
    """

    passwords: PasswordService
    tokens: TokenIssuer


class AuthenticationService:
    """Authenticate users and issue/validate access tokens (delegated JWT)."""

    def __init__(
        self,
        repository: UserRepository,
        deps: AuthenticationDeps,
    ) -> None:
        self._repository = repository
        self._passwords = deps.passwords
        self._tokens = deps.tokens

    async def authenticate(self, command: LoginCommand) -> User:
        """Return the active user for valid credentials, else raise.

        Mirrors the legacy ``/auth/token`` checks exactly: unknown email or a
        bad password raises :class:`InvalidCredentialsError`; a deactivated
        account raises :class:`InactiveUserError`.
        """
        user = await self._repository.get_by_email(command.email)
        if user is None or not self._passwords.verify(
            command.password, user.hashed_password
        ):
            raise InvalidCredentialsError(ERR_INVALID_CREDENTIALS)
        if not user.is_active:
            raise InactiveUserError(ERR_USER_INACTIVE)
        return user

    async def login(self, command: LoginCommand) -> AccessTokenView:
        """Authenticate and issue an access token in one step."""
        user = await self.authenticate(command)
        return self.issue_token(user)

    def issue_token(self, user: User) -> AccessTokenView:
        """Issue a signed access token for an already-authenticated user."""
        return AccessTokenView(access_token=self._tokens.create_access_token(user))

    def validate_token(self, token: str) -> dict[str, object] | None:
        """Decode/validate an access token; return its payload or ``None``."""
        return self._tokens.decode_access_token(token)


__all__ = [
    "AuthenticationDeps",
    "AuthenticationService",
    "InactiveUserError",
    "InvalidCredentialsError",
]
