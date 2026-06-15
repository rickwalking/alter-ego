"""Composition root for the editorial module — manual constructor injection.

``bootstrap_module`` wires the editorial application service to its
collaborators explicitly. There is no DI framework and no global container
lookup inside the module (ADR-0009 §9) — the inbound edge constructs the
request-scoped collaborators (which enlist in the request's Unit of Work) and
passes them in.

**Behavior-preserving wiring (AE-0108).** The editorial adapters are NOT
relocated in this phase; they remain at their legacy locations. The inbound
caller builds them exactly as the legacy carousel routes do today (the
request-scoped ``CarouselRepository``) and hands them to this bootstrap. The
collaborators are accepted via the typed :class:`EditorialAdapters` bundle so
the function keeps to a single grouped argument (backend/CLAUDE.md ≤3 args).

The ``PlatformServices`` protocol is a local placeholder (as in the reference
template and the conversation/knowledge modules) so the module is importable and
type-clean before ``rag_backend.platform`` ships its real type. A real module
reads database/session factories and telemetry from it to build adapters here
once it exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rag_backend.modules.editorial.application.service import EditorialService
from rag_backend.modules.editorial.domain.ports import CarouselRepository
from rag_backend.modules.editorial.infrastructure.legacy_carousel_acl import (
    LegacyCarouselAcl,
)
from rag_backend.platform.database import UnitOfWork


class PlatformServices(Protocol):
    """Placeholder for the shared platform substrate passed to bootstrap.

    Replaced by ``rag_backend.platform.PlatformServices`` once it exists.
    """


@dataclass(frozen=True)
class EditorialAdapters:
    """Pre-constructed, request-scoped collaborators for the editorial module.

    Built at the inbound edge (the api adapter / legacy carousel route) from the
    existing infrastructure so the module wires to them without relocation
    (AE-0108). The ``unit_of_work`` wraps that same request's ``AsyncSession``
    and is the single transaction owner the application service commits through
    (ADR-0009 §9).
    """

    repository: CarouselRepository
    unit_of_work: UnitOfWork
    legacy_carousel_acl: LegacyCarouselAcl | None = None


@dataclass(frozen=True)
class EditorialModule:
    """Public collaborators returned by :func:`bootstrap_module`.

    Bundles the editorial application service, the request-scoped Unit of Work,
    and the legacy carousel anti-corruption layer (AE-0109) so the inbound edge
    can resolve editorial operations, the single commit boundary, and the legacy
    persistence seam through the module facade (no behavior change; later phases
    move the carousel editorial workflow routes behind handlers that read/write
    through the ACL and commit via this UoW).
    """

    service: EditorialService
    unit_of_work: UnitOfWork
    legacy_carousel_acl: LegacyCarouselAcl | None = None


def bootstrap_module(
    platform: PlatformServices,
    adapters: EditorialAdapters,
) -> EditorialModule:
    """Wire the editorial module and return its public collaborators.

    ``platform`` is accepted to demonstrate the ADR-0009 §9 bootstrap signature
    (a real module builds adapters from it once ``rag_backend.platform`` ships).
    For the behavior-preserving phase the caller supplies the already-built
    legacy adapters via ``adapters``; this function injects the repository into
    the application service via the constructor.
    """
    _ = platform  # real modules construct adapters from platform services
    service = EditorialService(repository=adapters.repository)
    return EditorialModule(
        service=service,
        unit_of_work=adapters.unit_of_work,
        legacy_carousel_acl=adapters.legacy_carousel_acl,
    )
