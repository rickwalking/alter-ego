"""Outbound ports for the publishing bounded context.

The publishing ports are:

* ``BlogPostRepository`` — blog-post persistence (re-exported, object-identity
  shim; see below). The publishing context reads/lists blog posts through this
  contract.
* ``CarouselRepository`` — carousel project persistence (re-exported,
  object-identity shim; see below). The publishing context reads a carousel
  project's public-visibility signal (for the carousel→blog projection) through
  this contract.

The publishing-side blog read contract (``BlogPostReadPort``) lands in AE-0128
together with its concrete adapter + consumer, so the port and its implementation
arrive in one change (no port without a ``src`` consumer in the Wave-A skeleton).

Per backend/CLAUDE.md, interfaces are :class:`typing.Protocol`, never ABCs, and
they are fully typed (no ``Any``). These Protocols let the publishing
APPLICATION/domain layers depend only on contracts — never on the blog/carousel
ORM directly; the concrete persistence/distribution/outbox adapters arrive in
later phases (AE-0128..0130) behind this facade.

**Re-export, not relocation (AE-0126 constraint).** ``CarouselRepository`` is the
shared Protocol defined in ``rag_backend.domain.protocols.repositories`` (imported
by the carousel routes, the workflow engine, services, and the container).
``BlogPostRepository`` is the concrete data-access class defined in
``rag_backend.infrastructure.database.blog_post_repository`` (imported by the blog
routes). Physically moving either would break those imports, so this phase keeps
both definitions where they are and merely **re-exports** them here. The legacy
import paths keep resolving to the IDENTICAL objects, while the publishing module
domain layer also exposes them as its own ports. This mirrors
``modules.editorial.domain.ports`` / ``modules.presentation.domain.ports`` exactly
(object-identity shims).
"""

from __future__ import annotations

from rag_backend.domain.protocols.repositories import CarouselRepository
from rag_backend.infrastructure.database.blog_post_repository import (
    BlogPostRepository,
)

# NOTE: the publishing-side read contract over blog posts (BlogPostReadPort) is
# introduced in AE-0128 together with its concrete adapter + consumer, so the
# port and its implementation land in the same change (avoids a port with no
# src consumer). Wave A re-exports only the canonical repository ports.

__all__ = [
    "BlogPostRepository",
    "CarouselRepository",
]
