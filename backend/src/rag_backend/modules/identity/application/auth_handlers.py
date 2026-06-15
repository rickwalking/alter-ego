"""Auth command/query handlers for the identity bounded context (private).

The public facade re-exports :class:`AuthCommandHandler`; cross-module code and
the inbound HTTP adapters never import this path directly.

This is a **behavior-preserving** orchestration layer (AE-0099) over the AE-0098
``AuthenticationService`` and the user repository. Each handler maps a typed
auth command onto the exact persistence/JWT/bcrypt calls the legacy
``/api/auth`` routes make today, so the wire behavior (HS256 payload, bcrypt,
status codes, cookies) stays byte-identical when the routes move behind the
facade.

``change_password`` deliberately reproduces the legacy update path verbatim:
verify the current password first (the 401 guard runs *before* any write), then
set ``hashed_password`` and call ``repository.update`` inside the request-scoped
Unit of Work (the single commit owner, ADR-0009 §9). The legacy route's
known-and-snapshotted post-update lazy-load behavior is preserved because the
same repository ``update`` runs against the same session — no behavior is added
or papered over here (AE-0097 finding stays locked).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rag_backend.modules.identity.api.views import AccessTokenView
from rag_backend.modules.identity.application.authentication_service import (
    AuthenticationService,
)
from rag_backend.modules.identity.application.password_service import PasswordService
from rag_backend.modules.identity.application.user_service import (
    CurrentPasswordIncorrectError,
    UserNotFoundError,
)
from rag_backend.modules.identity.constants import (
    ERR_CURRENT_CREDENTIAL_INCORRECT,
    ERR_USER_NOT_FOUND,
)
from rag_backend.modules.identity.domain.commands import (
    ChangePasswordCommand,
    LoginCommand,
)
from rag_backend.modules.identity.domain.models import User
from rag_backend.modules.identity.domain.ports import UserRepository
from rag_backend.platform.database import UnitOfWork


@dataclass(frozen=True)
class AuthCommandDeps:
    """Collaborators grouped to keep the handler constructor at ≤3 arguments.

    Bundles the password service and the request-scoped Unit of Work so the
    user repository stays explicit while the constructor honours the
    backend/CLAUDE.md 3-argument limit.
    """

    passwords: PasswordService
    unit_of_work: UnitOfWork


class AuthCommandHandler:
    """Handle the ``/api/auth`` write/read use cases (login + change-password)."""

    def __init__(
        self,
        repository: UserRepository,
        authentication: AuthenticationService,
        deps: AuthCommandDeps,
    ) -> None:
        self._repository = repository
        self._authentication = authentication
        self._passwords = deps.passwords
        self._unit_of_work = deps.unit_of_work

    async def login(self, command: LoginCommand) -> AccessTokenView:
        """Authenticate credentials and issue an access token (delegated JWT)."""
        return await self._authentication.login(command)

    async def change_password(self, command: ChangePasswordCommand) -> None:
        """Change a user's password after verifying the current one.

        The wrong-current-password guard raises before any write (legacy 401
        ordering). On success the new hash is staged via ``repository.update``
        and committed once through the Unit of Work — the same single-statement
        path the legacy route ran, so the snapshotted contract is preserved.
        """
        user = await self._require_user(command.user_id)
        if not self._passwords.verify(command.current_password, user.hashed_password):
            raise CurrentPasswordIncorrectError(ERR_CURRENT_CREDENTIAL_INCORRECT)
        async with self._unit_of_work:
            user.hashed_password = self._passwords.hash(command.new_password)
            await self._repository.update(user)

    async def _require_user(self, user_id: UUID) -> User:
        user = await self._repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(ERR_USER_NOT_FOUND)
        return user


__all__ = [
    "AuthCommandDeps",
    "AuthCommandHandler",
]
