"""Outbound ports (Protocols) for the editorial bounded context.

The editorial port is:

* ``CarouselRepository`` — carousel project / slide / research-source /
  image-generation persistence (the editorial workflow's persistence boundary).

**Re-export, not relocation (AE-0108 constraint).** This Protocol is defined in
the SHARED protocol file ``rag_backend.domain.protocols.repositories`` which is
imported by the carousel routes, the workflow engine, services, and the
container. Physically moving the definition would break those imports, so this
phase keeps the definition where it is and merely **re-exports** it here. The
legacy import path
(``rag_backend.domain.protocols.repositories.CarouselRepository``) keeps
resolving to the IDENTICAL Protocol object, while the editorial module domain
layer also exposes it as its own port. Per backend/CLAUDE.md, interfaces are
``typing.Protocol``, never ABCs.

This mirrors ``modules.conversation.domain.ports`` exactly (object-identity
shim).
"""

from __future__ import annotations

from rag_backend.domain.protocols.repositories import CarouselRepository

__all__ = [
    "CarouselRepository",
]
