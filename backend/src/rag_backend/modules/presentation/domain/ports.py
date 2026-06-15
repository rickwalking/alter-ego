"""Outbound ports (Protocols) for the presentation bounded context.

The presentation ports are:

* ``CarouselRepository`` — carousel project / slide persistence (re-exported,
  object-identity shim; see below). The presentation context reads the project's
  presentation fields and its slides through this contract.
* ``PresentationPolicyPort`` — loading the versioned presentation policy
  (slide budgets, geometry, fonts) the renderer/validator enforces.
* ``SlideValidationPort`` — validating per-slide presentation copy against the
  active policy and returning a structured validation report.

Per backend/CLAUDE.md, interfaces are :class:`typing.Protocol`, never ABCs, and
they are fully typed (no ``Any``). These Protocols let the presentation
APPLICATION/domain layers depend only on contracts — never on the carousel ORM
or a concrete Postgres repository; the concrete adapters (provider ports,
persistence) arrive in later phases (AE-0118/0119) behind this facade.

**Re-export, not relocation (AE-0117 constraint) for ``CarouselRepository``.**
That Protocol is defined in the SHARED protocol file
``rag_backend.domain.protocols.repositories`` which is imported by the carousel
routes, the workflow engine, services, and the container. Physically moving the
definition would break those imports, so this phase keeps the definition where it
is and merely **re-exports** it here. The legacy import path
(``rag_backend.domain.protocols.repositories.CarouselRepository``) keeps
resolving to the IDENTICAL Protocol object, while the presentation module domain
layer also exposes it as its own port. This mirrors
``modules.editorial.domain.ports`` exactly (object-identity shim).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rag_backend.domain.protocols.repositories import CarouselRepository
from rag_backend.modules.presentation.domain.models import (
    CarouselPresentationPolicy,
    SlideValidationReport,
)


@runtime_checkable
class PresentationPolicyPort(Protocol):
    """Load the versioned presentation policy a project renders/validates against.

    Wraps the canonical policy-loading step so the application layer requests the
    active :class:`CarouselPresentationPolicy` through a contract instead of
    reaching into the policy loader directly. The concrete adapter (AE-0119)
    delegates to the unchanged policy source so the loaded policy stays
    byte-identical.
    """

    async def load_policy(self, version: str) -> CarouselPresentationPolicy:
        """Return the typed presentation policy for the given version."""
        ...


@runtime_checkable
class SlideValidationPort(Protocol):
    """Validate per-slide presentation copy against the active policy.

    Implementations delegate to the unchanged slide-validation logic and return
    the canonical :class:`SlideValidationReport` so the validation behavior +
    report shape stay byte-identical. The application layer forwards the report
    opaquely; this contract introduces no behavior change.
    """

    async def validate_slides(self, project_id: str) -> SlideValidationReport:
        """Validate the project's slides and return a structured report."""
        ...


__all__ = [
    "CarouselRepository",
    "PresentationPolicyPort",
    "SlideValidationPort",
]
