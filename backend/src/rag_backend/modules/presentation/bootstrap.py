"""Composition root for the presentation module — manual constructor injection.

``bootstrap_module`` wires the presentation application service to its
collaborators explicitly. There is no DI framework and no global container
lookup inside the module (ADR-0009 §9) — the inbound edge constructs the
request-scoped collaborators (which enlist in the request's Unit of Work) and
passes them in.

**Behavior-preserving wiring (AE-0117).** The presentation adapters are NOT
relocated in this phase; the inbound caller builds the request-scoped
``CarouselRepository`` exactly as the legacy carousel routes do today and hands
it (with the request's Unit of Work) to this bootstrap. The collaborators are
accepted via the typed :class:`PresentationAdapters` bundle so the function keeps
to a single grouped argument (backend/CLAUDE.md ≤3 args). Provider ports
(policy/slide-validation) arrive in AE-0119; until then the service stays
repository-only.

The ``PlatformServices`` protocol is a local placeholder (as in the reference
template and the editorial module) so the module is importable and type-clean
before ``rag_backend.platform`` ships its real type. A real module reads
database/session factories and telemetry from it to build adapters here once it
exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rag_backend.modules.presentation.application.service import (
    PresentationPorts,
    PresentationService,
)
from rag_backend.modules.presentation.domain.ports import (
    CarouselRepository,
    PresentationPolicyPort,
    SlideValidationPort,
)
from rag_backend.platform.database import UnitOfWork


class PlatformServices(Protocol):
    """Placeholder for the shared platform substrate passed to bootstrap.

    Replaced by ``rag_backend.platform.PlatformServices`` once it exists.
    """


@dataclass(frozen=True)
class PresentationAdapters:
    """Pre-constructed, request-scoped collaborators for the presentation module.

    Built at the inbound edge (the api adapter / legacy carousel route) from the
    existing infrastructure so the module wires to them without relocation
    (AE-0117). The ``unit_of_work`` wraps that same request's ``AsyncSession``
    and is the single transaction owner the application service commits through
    (ADR-0009 §9). The provider ports are optional until AE-0119 supplies them.
    """

    repository: CarouselRepository
    unit_of_work: UnitOfWork
    policy: PresentationPolicyPort | None = None
    slide_validation: SlideValidationPort | None = None


@dataclass(frozen=True)
class PresentationModule:
    """Public collaborators returned by :func:`bootstrap_module`.

    Bundles the presentation application service and the request-scoped Unit of
    Work so the inbound edge can resolve presentation operations and the single
    commit boundary through the module facade (no behavior change; later phases
    move the carousel presentation routes behind handlers that read/validate
    through the ports and commit via this UoW).
    """

    service: PresentationService
    unit_of_work: UnitOfWork


def bootstrap_module(
    platform: PlatformServices,
    adapters: PresentationAdapters,
) -> PresentationModule:
    """Wire the presentation module and return its public collaborators.

    ``platform`` is accepted to demonstrate the ADR-0009 §9 bootstrap signature
    (a real module builds adapters from it once ``rag_backend.platform`` ships).
    For the behavior-preserving phase the caller supplies the already-built
    request-scoped repository (and any provider ports) via ``adapters``; this
    function injects them into the application service via the constructor.
    """
    _ = platform  # real modules construct adapters from platform services
    service = PresentationService(
        repository=adapters.repository,
        ports=PresentationPorts(
            policy=adapters.policy,
            slide_validation=adapters.slide_validation,
        ),
    )
    return PresentationModule(
        service=service,
        unit_of_work=adapters.unit_of_work,
    )


__all__ = [
    "PresentationAdapters",
    "PresentationModule",
    "bootstrap_module",
]
