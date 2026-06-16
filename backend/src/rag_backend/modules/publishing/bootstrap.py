"""Composition root for the publishing module — manual constructor injection.

``bootstrap_module`` wires the publishing application service to its
collaborators explicitly. There is no DI framework and no global container
lookup inside the module (ADR-0009 §9) — the inbound edge constructs the
request-scoped collaborators (which enlist in the request's Unit of Work) and
passes them in.

**Behavior-preserving wiring (AE-0126/0128).** The publishing adapters are NOT
relocated; the inbound caller builds the request-scoped ``CarouselRepository``
and the AE-0128 :class:`LegacyPublishingAcl` (the sole carousel/blog ORM seam)
exactly as the legacy carousel/blog routes do today and hands them (with the
request's Unit of Work) to this bootstrap. The collaborators are accepted via the
typed :class:`PublishingAdapters` bundle so the function keeps to a single grouped
argument (backend/CLAUDE.md ≤3 args). AE-0128 wires the carousel-release,
blog-visibility, and blog-schedule ports (backed by the ACL) into the service so
the carousel publish flow + the standalone blog publish/unpublish/schedule routes
+ the scheduled-publish worker route through the publishing facade. The additive
outbox arrives in AE-0130.

The ``PlatformServices`` protocol is a local placeholder (as in the reference
template and the editorial/presentation modules) so the module is importable and
type-clean before ``rag_backend.platform`` ships its real type. A real module
reads database/session factories and telemetry from it to build adapters here
once it exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rag_backend.modules.publishing.application.service import (
    PublishingPorts,
    PublishingService,
)
from rag_backend.modules.publishing.domain.ports import (
    BlogPostRepository,
    CarouselRepository,
)
from rag_backend.modules.publishing.infrastructure.legacy_publishing_acl import (
    LegacyPublishingAcl,
)
from rag_backend.modules.publishing.infrastructure.publishing_port_adapters import (
    AclBlogScheduleAdapter,
    AclBlogVisibilityAdapter,
    AclCarouselReleaseAdapter,
)
from rag_backend.platform.database import UnitOfWork


class PlatformServices(Protocol):
    """Placeholder for the shared platform substrate passed to bootstrap.

    Replaced by ``rag_backend.platform.PlatformServices`` once it exists.
    """


@dataclass(frozen=True)
class PublishingAdapters:
    """Pre-constructed, request-scoped collaborators for the publishing module.

    Built at the inbound edge (the api adapter / legacy carousel + blog routes)
    from the existing infrastructure so the module wires to them without
    relocation (AE-0126/0128). The ``unit_of_work`` wraps that same request's
    ``AsyncSession`` and is the single transaction owner the application service
    commits through (ADR-0009 §9). The AE-0128 :class:`LegacyPublishingAcl` (the
    sole carousel/blog ORM seam) backs the release/visibility/schedule ports; it
    is optional so the AE-0126 scaffolding bootstrap keeps working (service stays
    carousel-repository-only when absent).
    """

    carousel_repository: CarouselRepository
    unit_of_work: UnitOfWork
    blog_repository: BlogPostRepository | None = None
    publishing_acl: LegacyPublishingAcl | None = None


@dataclass(frozen=True)
class PublishingModule:
    """Public collaborators returned by :func:`bootstrap_module`.

    Bundles the publishing application service and the request-scoped Unit of
    Work so the inbound edge can resolve publishing operations and the single
    commit boundary through the module facade (no behavior change). The carousel
    publish flow + the standalone blog publish/unpublish/schedule routes + the
    scheduled-publish worker resolve their writes through ``service`` (over the
    AE-0128 release/visibility/schedule ports) and commit via this UoW.
    """

    service: PublishingService
    unit_of_work: UnitOfWork


def bootstrap_module(
    platform: PlatformServices,
    adapters: PublishingAdapters,
) -> PublishingModule:
    """Wire the publishing module and return its public collaborators.

    ``platform`` is accepted to demonstrate the ADR-0009 §9 bootstrap signature
    (a real module builds adapters from it once ``rag_backend.platform`` ships).
    For the behavior-preserving phase the caller supplies the already-built
    request-scoped carousel repository + the AE-0128 ACL via ``adapters``; this
    function injects them (the ACL-backed release/visibility/schedule ports) into
    the application service via the constructor.
    """
    _ = platform  # real modules construct adapters from platform services
    service = PublishingService(
        carousel_repository=adapters.carousel_repository,
        ports=_build_ports(adapters.blog_repository, adapters.publishing_acl),
    )
    return PublishingModule(
        service=service,
        unit_of_work=adapters.unit_of_work,
    )


def _build_ports(
    blog_repository: BlogPostRepository | None,
    acl: LegacyPublishingAcl | None,
) -> PublishingPorts:
    """Build the ACL-backed publishing ports, when the ACL is available (AE-0128).

    The carousel-release, blog-visibility, and blog-schedule ports are all backed
    by the AE-0128 :class:`LegacyPublishingAcl` (the sole carousel/blog ORM seam →
    the byte-identical legacy writes). When no ACL is supplied (the AE-0126
    scaffolding bootstrap) the service stays carousel-repository-only.
    """
    if acl is None:
        return PublishingPorts(blog_repository=blog_repository)
    return PublishingPorts(
        blog_repository=blog_repository,
        carousel_release=AclCarouselReleaseAdapter(acl),
        blog_visibility=AclBlogVisibilityAdapter(acl),
        blog_schedule=AclBlogScheduleAdapter(acl),
    )


__all__ = [
    "PublishingAdapters",
    "PublishingModule",
    "bootstrap_module",
]
