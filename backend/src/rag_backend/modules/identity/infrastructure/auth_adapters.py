"""Concrete identity adapters delegating to the UNCHANGED ``infrastructure.auth``.

These adapters satisfy the application-layer
:class:`~rag_backend.modules.identity.application.ports.PasswordHasher` and
:class:`~rag_backend.modules.identity.application.ports.TokenIssuer` Protocols by
forwarding to the existing ``rag_backend.infrastructure.auth`` functions
(``hash_password``/``verify_password``/``create_access_token``/
``decode_access_token``). No JWT or bcrypt logic is reimplemented here (AE-0098):
this is a thin, behavior-preserving boundary so the application layer stays free
of direct ``infrastructure.auth`` imports while the HS256 payload, algorithm,
expiry, and bcrypt parameters remain byte-identical.

The infrastructure layer is the legal place to import the concrete
``infrastructure.auth`` module; the adapters are wired into the services in
``bootstrap.py`` via manual constructor injection.
"""

from __future__ import annotations

from rag_backend.infrastructure.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.identity.domain.models import User


class BcryptPasswordHasher:
    """``PasswordHasher`` backed by ``infrastructure.auth`` bcrypt helpers.

    Stateless: the methods are ``staticmethod``\\s that forward to the module
    functions. A staticmethod still satisfies the instance-method shape the
    ``PasswordHasher`` Protocol declares (it is accessed as a callable attribute
    with the same signature), so the adapter conforms structurally.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """Return the bcrypt hash of ``password`` (delegates, no reimpl)."""
        return hash_password(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Return True when the password matches (delegates, no reimpl)."""
        return verify_password(plain_password, hashed_password)


class JwtTokenIssuer:
    """``TokenIssuer`` backed by ``infrastructure.auth`` HS256 JWT helpers.

    Holds the request/app ``Settings`` (secret keys + expiry) so the module
    services issue and validate tokens with the same parameters as the legacy
    routes, which is what keeps the wire behavior identical.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_access_token(self, user: User) -> str:
        """Issue a signed JWT access token for ``user`` (delegates, no reimpl)."""
        return create_access_token(self._settings, user)

    def decode_access_token(self, token: str) -> dict[str, object] | None:
        """Decode/validate a JWT access token (delegates, no reimpl)."""
        return decode_access_token(self._settings, token)


__all__ = [
    "BcryptPasswordHasher",
    "JwtTokenIssuer",
]
