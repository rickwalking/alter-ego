"""Password use cases for the identity bounded context (private to the module).

The public facade re-exports this under ``PasswordService``; cross-module code
never imports this path directly.

This is a **behavior-preserving** facade over the existing bcrypt helpers
(AE-0098): hashing and verification delegate to the injected
:class:`~rag_backend.modules.identity.application.ports.PasswordHasher`, which
wraps the UNCHANGED ``infrastructure.auth`` functions. The service adds the
explicit minimum-length policy that the legacy API enforced at the schema edge
(``MIN_PASSWORD_LENGTH``), so policy lives in one typed place.
"""

from __future__ import annotations

from rag_backend.domain.constants import MIN_PASSWORD_LENGTH
from rag_backend.modules.identity.application.ports import PasswordHasher
from rag_backend.modules.identity.constants import ERR_CREDENTIAL_TOO_SHORT


class PasswordService:
    """Hash, verify, and policy-check passwords (delegates bcrypt to the port)."""

    def __init__(self, hasher: PasswordHasher) -> None:
        self._hasher = hasher

    def hash(self, password: str) -> str:
        """Return the bcrypt hash of a policy-compliant password.

        Enforces the minimum-length policy before hashing so a too-short
        password is rejected at the service boundary (raises ``ValueError``).
        """
        self.enforce_policy(password)
        return self._hasher.hash_password(password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Return True when ``plain_password`` matches ``hashed_password``."""
        return self._hasher.verify_password(plain_password, hashed_password)

    @staticmethod
    def enforce_policy(password: str) -> None:
        """Raise ``ValueError`` when ``password`` is shorter than the minimum."""
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(ERR_CREDENTIAL_TOO_SHORT)

    @staticmethod
    def meets_policy(password: str) -> bool:
        """Return True when ``password`` satisfies the minimum-length policy."""
        return len(password) >= MIN_PASSWORD_LENGTH


__all__ = [
    "PasswordService",
]
