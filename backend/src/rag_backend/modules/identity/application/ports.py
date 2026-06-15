"""Application-layer collaborator ports for the identity bounded context.

The identity services delegate all JWT and bcrypt work to the UNCHANGED
``rag_backend.infrastructure.auth`` module (AE-0098 constraint — JWT/bcrypt are
not reimplemented). To keep the application/domain layers free of direct
infrastructure imports (Clean Architecture; the module exit-gate convention,
module-conventions.md §7d), the concrete ``infrastructure.auth`` functions are
adapted to these Protocols in ``bootstrap.py`` and injected via the constructor.

* ``PasswordHasher`` — wraps ``hash_password`` / ``verify_password`` (bcrypt).
* ``TokenIssuer`` — wraps ``create_access_token`` / ``decode_access_token``
  (HS256 JWT). The token payload, algorithm, and expiry stay byte-identical to
  the legacy behavior because the adapter calls the same functions.
"""

from __future__ import annotations

from typing import Protocol

from rag_backend.modules.identity.domain.models import User


class PasswordHasher(Protocol):
    """Password hashing/verification port (bcrypt under the hood)."""

    def hash_password(self, password: str) -> str:
        """Return the bcrypt hash of ``password``."""
        ...

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Return True when ``plain_password`` matches ``hashed_password``."""
        ...


class TokenIssuer(Protocol):
    """JWT access-token issue/validate port (HS256 under the hood)."""

    def create_access_token(self, user: User) -> str:
        """Issue a signed JWT access token for ``user``."""
        ...

    def decode_access_token(self, token: str) -> dict[str, object] | None:
        """Decode/validate a JWT access token; return its payload or ``None``."""
        ...


__all__ = [
    "PasswordHasher",
    "TokenIssuer",
]
