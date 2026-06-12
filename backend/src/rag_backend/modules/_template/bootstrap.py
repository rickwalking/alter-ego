"""Composition root for the template module — manual constructor injection.

``bootstrap_module`` receives the shared platform services and constructs the
module's adapters and application services explicitly. There is no DI
framework and no global container lookup (ADR-0009 §9).

The ``PlatformServices`` protocol below is a **local placeholder** so the
template is importable and type-clean today. When ``rag_backend.platform``
ships its real ``PlatformServices`` (ADR-0009 §9), a real module imports that
type here instead. Real modules also create the request-scoped Unit of Work
at the inbound edge and pass it into services; this skeleton omits the UoW to
avoid coupling to not-yet-built platform plumbing.
"""

from __future__ import annotations

from typing import Protocol

from rag_backend.modules._template.application.service import TemplateService
from rag_backend.modules._template.infrastructure.repository import (
    InMemoryTemplateRepository,
)


class PlatformServices(Protocol):
    """Placeholder for the shared platform substrate passed to bootstrap.

    Replaced by ``rag_backend.platform.PlatformServices`` once it exists. A
    real module reads database/session factories, messaging, config, logging,
    and telemetry from here to build its adapters.
    """


def bootstrap_module(platform: PlatformServices) -> TemplateService:
    """Wire the template module and return its public application service.

    ``platform`` is accepted to demonstrate the ADR-0009 §9 bootstrap
    signature; this skeleton builds an in-memory adapter and does not yet read
    from it. A real module constructs its infrastructure adapters from
    ``platform`` and injects them into its application services here.
    """
    _ = platform  # real modules construct adapters from platform services
    repository = InMemoryTemplateRepository()
    return TemplateService(repository=repository)
