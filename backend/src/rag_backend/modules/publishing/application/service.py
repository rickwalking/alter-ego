"""Application service (use case) for the publishing bounded context.

Private to the module. The public facade re-exports this type under its public
name; cross-module code never imports this path directly.

The service wires to the publishing **ports** (Protocols / re-exported
repositories in ``rag_backend.modules.publishing.domain.ports``) via manual
constructor injection (ADR-0009 §9). It depends ONLY on those contracts — never
on the blog/carousel ORM or a concrete persistence class directly — so the
persistence details stay behind the adapters built at the inbound edge (the
publishing ACL/owner in the infrastructure layer).

It exposes:

* ``get_publication`` — the carousel→blog read projection (scaffolding; AE-0131
  delivers the full projection). Reads a carousel project via the injected
  ``CarouselRepository`` and wraps it as a :class:`Publication` view.
* ``release_carousel`` — the carousel public-release write use case (AE-0128).
  Forwards to the :class:`CarouselReleaseHandler` over the
  :class:`CarouselReleasePort`; byte-identical to the legacy ``is_public`` write.
* ``publish_blog`` / ``unpublish_blog`` — the standalone blog visibility writes
  (AE-0128) over the :class:`BlogVisibilityPort` (flush only; the route commits).
* ``schedule_blog`` / ``process_due_blog_posts`` — the standalone blog scheduling
  writes (AE-0128) over the :class:`BlogSchedulePort`.

Behavior-preserving: each method forwards to an injected port/adapter; no
publish/visibility/schedule behavior is changed (AE-0128 is a contract relocation,
not an auto-publish cutover). A use case whose port is absent raises a clear
:class:`RuntimeError` rather than silently no-op'ing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from rag_backend.modules.publishing.application.release_command import (
    CarouselReleaseCommand,
    CarouselReleaseHandler,
)
from rag_backend.modules.publishing.domain.models import Publication
from rag_backend.modules.publishing.domain.ports import (
    BlogPostRepository,
    BlogSchedulePort,
    BlogVisibilityPort,
    CarouselReleasePort,
    CarouselRepository,
)

# Programmer-error sentinels for a use case invoked without its required port; the
# inbound edge always wires the ports, so these signal a wiring bug, never a path
# a request can reach in production.
_ERR_NO_RELEASE_PORT = "publishing service invoked without the carousel release port"
_ERR_NO_VISIBILITY_PORT = "publishing service invoked without the blog visibility port"
_ERR_NO_SCHEDULE_PORT = "publishing service invoked without the blog schedule port"


@dataclass(frozen=True)
class PublishingPorts:
    """Optional publishing ports the service forwards to.

    Grouped into one typed bundle so the service keeps to a single grouped
    argument beyond the carousel repository (backend/CLAUDE.md ≤3 args). Each
    port is optional so the AE-0126 scaffolding keeps working; a use case whose
    port is absent raises a clear :class:`RuntimeError` rather than silently
    no-op'ing. The AE-0128 release/visibility/schedule ports are wired at the
    inbound edge from the publishing ACL/owner.
    """

    blog_repository: BlogPostRepository | None = None
    carousel_release: CarouselReleasePort | None = None
    blog_visibility: BlogVisibilityPort | None = None
    blog_schedule: BlogSchedulePort | None = None


class PublishingService:
    """Coordinates publishing use cases over the publishing ports.

    Dependencies are injected through the constructor (manual constructor
    injection, ADR-0009 §9). The single transaction owner (Unit of Work) is
    supplied to the inbound edge via the module's bootstrap; the write use cases
    forward to ports whose adapters stage through that owner.
    """

    def __init__(
        self,
        carousel_repository: CarouselRepository,
        ports: PublishingPorts | None = None,
    ) -> None:
        self._carousel_repository = carousel_repository
        self._ports = ports or PublishingPorts()

    async def get_publication(self, project_id: UUID) -> Publication | None:
        """Return the carousel→blog publication view, or ``None`` if absent."""
        project = await self._carousel_repository.get_project_by_id(project_id)
        if project is None:
            return None
        return Publication(project=project)

    async def release_carousel(self, command: CarouselReleaseCommand) -> object:
        """Release a carousel publicly; return the updated carousel entity.

        Byte-identical to the legacy ``crud.py:publish_carousel`` ``is_public``
        write — forwards to the :class:`CarouselReleaseHandler` over the release
        port (the ACL/owner performs the entity + ORM write and the single commit).
        """
        port = self._ports.carousel_release
        if port is None:
            raise RuntimeError(_ERR_NO_RELEASE_PORT)
        return await CarouselReleaseHandler(port).release(command)

    async def publish_blog(self, post: object) -> None:
        """Publish a standalone blog post (visibility-status write; flush only)."""
        port = self._require_visibility_port()
        await port.mark_published(post)

    async def unpublish_blog(self, post: object) -> None:
        """Unpublish a standalone blog post (visibility-status write; flush only)."""
        port = self._require_visibility_port()
        await port.mark_unpublished(post)

    async def schedule_blog(self, post: object, scheduled_at: datetime) -> None:
        """Schedule a standalone blog post for future publication (flush only)."""
        port = self._require_schedule_port()
        await port.schedule_publish(post, scheduled_at)

    async def process_due_blog_posts(self) -> int:
        """Publish all blog posts whose scheduled time has passed; return count."""
        port = self._require_schedule_port()
        return await port.process_due_posts()

    def _require_visibility_port(self) -> BlogVisibilityPort:
        port = self._ports.blog_visibility
        if port is None:
            raise RuntimeError(_ERR_NO_VISIBILITY_PORT)
        return port

    def _require_schedule_port(self) -> BlogSchedulePort:
        port = self._ports.blog_schedule
        if port is None:
            raise RuntimeError(_ERR_NO_SCHEDULE_PORT)
        return port


__all__ = [
    "PublishingPorts",
    "PublishingService",
]
