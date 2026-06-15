"""Application service (use case) for the publishing bounded context.

Private to the module. The public facade re-exports this type under its public
name; cross-module code never imports this path directly.

The service wires to the publishing **ports** (Protocols / re-exported
repositories in ``rag_backend.modules.publishing.domain.ports``) via manual
constructor injection (ADR-0009 §9). It depends ONLY on those contracts — never
on the blog/carousel ORM or a concrete persistence class directly — so the
persistence/distribution details stay behind the adapters built at the inbound
edge (later phases AE-0128..0130).

It exposes:

* ``get_publication`` — the carousel→blog read projection (scaffolding; AE-0131
  delivers the full projection). Reads a carousel project via the injected
  ``CarouselRepository`` and wraps it as a :class:`Publication` view.

Behavior-preserving: the method forwards to an injected repository port; no
publish behavior is changed in AE-0126.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rag_backend.modules.publishing.domain.models import Publication
from rag_backend.modules.publishing.domain.ports import (
    BlogPostRepository,
    CarouselRepository,
)


@dataclass(frozen=True)
class PublishingPorts:
    """Optional publishing ports the service forwards to.

    Grouped into one typed bundle so the service keeps to a single grouped
    argument beyond the carousel repository (backend/CLAUDE.md ≤3 args). Each
    port is optional so the AE-0126 scaffolding keeps working; a use case whose
    port is absent raises a clear :class:`RuntimeError` rather than silently
    no-op'ing. The blog read/persistence ports arrive in AE-0128.
    """

    blog_repository: BlogPostRepository | None = None


class PublishingService:
    """Coordinates publishing use cases over the publishing ports.

    Dependencies are injected through the constructor (manual constructor
    injection, ADR-0009 §9). The single transaction owner (Unit of Work) is
    supplied to the inbound edge via the module's bootstrap; the write use cases
    (later phases) forward to ports whose adapters stage through that owner.
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


__all__ = [
    "PublishingPorts",
    "PublishingService",
]
