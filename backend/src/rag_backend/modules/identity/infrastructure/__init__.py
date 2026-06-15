"""Infrastructure layer for the identity bounded context (private).

**JWT/bcrypt are NOT reimplemented or relocated (AE-0098).** The single source
of JWT/bcrypt logic stays at ``rag_backend.infrastructure.auth`` and the user
persistence adapter stays at
``rag_backend.infrastructure.database.user_repository``. This subpackage holds
only the thin adapters that forward the application-layer ports to those
existing functions (see ``auth_adapters.py``); the module's
:func:`~rag_backend.modules.identity.bootstrap.bootstrap_module` wires them via
manual constructor injection. Physical relocation of the user repository is
deferred to a later phase.
"""

from rag_backend.modules.identity.infrastructure.auth_adapters import (
    BcryptPasswordHasher,
    JwtTokenIssuer,
)

__all__ = [
    "BcryptPasswordHasher",
    "JwtTokenIssuer",
]
