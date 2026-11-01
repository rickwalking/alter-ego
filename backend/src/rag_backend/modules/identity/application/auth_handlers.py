"""Auth command/query handlers for the identity bounded context (private).

The public facade re-exports :class:`AuthCommandHandler`; cross-module code and
the inbound HTTP adapters never import this path directly.

This is a **behavior-preserving** orchestration layer over the ``AuthenticationService``
and the user repository. Each handler maps a typed
auth command onto the exact persistence/JWT/bcrypt calls the legacy
``/api/auth`` routes make today, so the wire behavior (HS256 payload, bcrypt,
status codes, cookies) stays byte-identical when the routes move behind the
facade.

``change_password`` reproduces the legacy update path: verify the current
password first (the 401 guard runs *before* any write), then set the new hash,
clear ``must_change_password``, bump the token version (which logs out every
other session) and call ``repository.update`` inside the request-scoped
Unit of Work (the single commit owner, ADR-0009 §9). The repository refreshes
the user after its flush, so a password-only update returns the stored row
instead of lazy-loading the database-set ``updated_at`` (which used to 500).
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
    UserNotFoundError,
    new_password_hash,
)
from rag_backend.modules.identity.constants import ERR_USER_NOT_FOUND
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

    async def change_password(self, command: ChangePasswordCommand) -> AccessTokenView:
        """Change a user's password after verifying the current one.

        The wrong-current-password and unchanged-password guards raise before
        any write (legacy 401 ordering). On success the new hash is staged, the
        forced-change flag cleared and the token version bumped via
        ``repository.update``, committed once through the Unit of Work. Every
        token issued before is now stale; the returned fresh token, at the new
        version, keeps the caller signed in. The user row is read locked (and
        stays locked until the commit), so the bump is atomic.
        """
        user = await self._require_locked_user(command.user_id)
        new_hash = new_password_hash(self._passwords, user, command)
        async with self._unit_of_work:
            user.change_password(new_hash)
            updated = await self._repository.update(user)
        return self._authentication.issue_token(updated)

    async def _require_locked_user(self, user_id: UUID) -> User:
        """The user with its row locked, so concurrent changes run one at a time.

        A second change waits for the first to commit, then sees its new hash
        and token version: it cannot bump from the same version again.
        """
        user = await self._repository.get_by_id_for_update(user_id)
        if user is None:
            raise UserNotFoundError(ERR_USER_NOT_FOUND)
        return user


__all__ = [
    "AuthCommandDeps",
    "AuthCommandHandler",
]
