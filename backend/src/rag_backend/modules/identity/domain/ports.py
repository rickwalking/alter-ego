"""Outbound ports (Protocols) for the identity bounded context.

The identity port is:

* ``UserRepository`` — user persistence (create/get/list/update/delete/count).

**Re-export, not relocation (AE-0098 / behavior-preserving).** The
``UserRepository`` Protocol is defined in the SHARED protocol file
``rag_backend.domain.protocols.repositories`` which is imported by ~50+
non-identity callers (the container, routes, dependencies, the Postgres
adapter). Physically moving the definition would break those imports, so this
phase keeps the definition where it is and merely **re-exports** it here. The
legacy import path
(``rag_backend.domain.protocols.repositories.UserRepository``) keeps resolving
to the IDENTICAL Protocol object, while the module domain layer also exposes it
as its own port. Per backend/CLAUDE.md, interfaces are ``typing.Protocol``,
never ABCs.
"""

from __future__ import annotations

from rag_backend.domain.protocols.repositories import UserRepository

__all__ = [
    "UserRepository",
]
