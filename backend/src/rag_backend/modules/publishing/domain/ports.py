"""Outbound ports for the publishing bounded context.

The publishing ports are:

* ``BlogPostRepository`` — blog-post persistence (re-exported, object-identity
  shim; see below). The publishing context reads/lists blog posts through this
  contract.
* ``CarouselRepository`` — carousel project persistence (re-exported,
  object-identity shim; see below). The publishing context reads a carousel
  project's public-visibility signal (for the carousel→blog projection) through
  this contract.
* ``CarouselReleasePort`` — the public-release (``is_public``) write contract for
  a carousel project (AE-0128). The carousel publish flow drives the
  ``is_public=True`` release through this port; its only adapter is the
  publishing ACL/owner, which is the sole publishing code touching the carousel
  ORM for this write.
* ``BlogVisibilityPort`` — the publish/unpublish status-write contract for a
  standalone blog post (AE-0128). The standalone blog publish/unpublish routes
  drive their visibility-status writes through this port (adapter: the ACL/owner).
* ``BlogSchedulePort`` — the scheduling write contract for a standalone blog post
  (AE-0128). The standalone blog schedule route + the scheduled-publish worker
  drive their schedule writes through this port (adapter: the ACL/owner).

Per backend/CLAUDE.md, interfaces are :class:`typing.Protocol`, never ABCs, and
they are fully typed (no ``Any``). These Protocols let the publishing
APPLICATION/domain layers depend only on contracts — never on the blog/carousel
ORM directly; the concrete persistence adapters live in the publishing
infrastructure ACL/owner behind this facade (AE-0128).

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

**No ORM in domain (AE-0128 constraint).** The three new write Protocols
(``CarouselReleasePort`` / ``BlogVisibilityPort`` / ``BlogSchedulePort``) speak
only in primitive/value types (ids, the optional scheduled instant). The carousel
project ENTITY is passed through ``object`` (the application layer holds the
canonical :class:`CarouselProject`; the port stays ORM-free and the adapter casts
it back) so neither this domain layer nor the application layer imports the ORM.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from rag_backend.domain.protocols.repositories import CarouselRepository
from rag_backend.infrastructure.database.blog_post_repository import (
    BlogPostRepository,
)


class CarouselReleasePort(Protocol):
    """Public-release (``is_public``) write contract for a carousel project.

    The single seam through which the carousel publish flow makes a project
    publicly visible. The concrete adapter (the publishing ACL/owner) performs the
    byte-identical ``is_public=True`` / ``current_phase=published`` write through
    the carousel repository AND the carousel ORM row and commits via the platform
    Unit of Work — exactly the legacy ``crud.py:publish_carousel`` release write.
    """

    async def release_public(
        self,
        project: object,
        project_id: str,
    ) -> object:
        """Mark the carousel publicly released; return the updated entity.

        ``project`` is the canonical carousel project entity (passed as
        ``object`` so the domain port stays ORM-free); ``project_id`` is its id.
        Returns the updated carousel entity the route serializes (identical to the
        legacy ``repo.update_project`` return).
        """
        ...


class BlogVisibilityPort(Protocol):
    """Publish/unpublish status-write contract for a standalone blog post.

    The seam the standalone blog publish/unpublish routes drive their
    visibility-status writes through. The concrete adapter (the publishing
    ACL/owner) performs the byte-identical status / ``published_at`` writes on the
    blog row (flush only; the route owns the event emission + the single commit).
    """

    async def mark_published(self, post: object) -> None:
        """Set the blog row to PUBLISHED with ``published_at`` now (flush only)."""
        ...

    async def mark_unpublished(self, post: object) -> None:
        """Revert the blog row to DRAFT and clear publish stamps (flush only)."""
        ...


class BlogSchedulePort(Protocol):
    """Scheduling write contract for a standalone blog post.

    The seam the standalone blog schedule route + the scheduled-publish worker
    drive their schedule writes through. The concrete adapter (the publishing
    ACL/owner) performs the byte-identical ``scheduled_publish_at`` write + the
    scheduled-publish event emission (flush only; the route owns the commit), and
    the due-post sweep that publishes posts whose scheduled instant has passed.
    """

    async def schedule_publish(self, post: object, scheduled_at: datetime) -> None:
        """Stamp ``scheduled_publish_at`` + emit the scheduled event (flush only)."""
        ...

    async def process_due_posts(self) -> int:
        """Publish all posts whose scheduled time has passed; return the count."""
        ...


__all__ = [
    "BlogPostRepository",
    "BlogSchedulePort",
    "BlogVisibilityPort",
    "CarouselReleasePort",
    "CarouselRepository",
]
