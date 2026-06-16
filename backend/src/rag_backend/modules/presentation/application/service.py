"""Application service (use case) for the presentation bounded context.

Private to the module. The public facade re-exports this type under its public
name; cross-module code never imports this path directly.

The service wires to the presentation **ports** (Protocols in
``rag_backend.modules.presentation.domain.ports``) via manual constructor
injection (ADR-0009 §9). It depends ONLY on those contracts — never on the
carousel ORM or a concrete Postgres repository — so the persistence/policy
details stay behind the adapters built at the inbound edge (AE-0118/0119).

It exposes:

* ``get_presentation`` — the presentation aggregate VIEW read (scaffolding);
* ``load_policy`` — the active presentation policy (``PresentationPolicyPort``);
* ``validate_slides`` — per-slide presentation validation
  (``SlideValidationPort``).

Behavior-preserving: every method forwards to an injected port (or the
repository), whose adapter delegates to the unchanged infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rag_backend.modules.presentation.domain.models import (
    CarouselPresentationPolicy,
    PresentationProject,
    SlideValidationReport,
)
from rag_backend.modules.presentation.domain.ports import (
    CarouselRepository,
    PresentationPolicyPort,
    SlideValidationPort,
)


@dataclass(frozen=True)
class PresentationPorts:
    """Optional presentation ports the service forwards to.

    Grouped into one typed bundle so the service keeps to a single grouped
    argument beyond the repository (backend/CLAUDE.md ≤3 args). Each port is
    optional so the scaffolding (repository-only) keeps working; a method whose
    port is absent raises a clear :class:`RuntimeError` rather than silently
    no-op'ing.
    """

    policy: PresentationPolicyPort | None = None
    slide_validation: SlideValidationPort | None = None


class PresentationService:
    """Coordinates presentation use cases over the presentation ports.

    Dependencies are injected through the constructor (manual constructor
    injection, ADR-0009 §9). The single transaction owner (Unit of Work) is
    supplied to the inbound edge via the module's bootstrap; the use cases here
    forward to ports whose adapters stage through that owner.
    """

    def __init__(
        self,
        repository: CarouselRepository,
        ports: PresentationPorts | None = None,
    ) -> None:
        self._repository = repository
        self._ports = ports or PresentationPorts()

    async def get_presentation(
        self,
        project_id: UUID,
    ) -> PresentationProject | None:
        """Return the presentation VIEW for a project, or ``None`` if absent."""
        project = await self._repository.get_project_by_id(project_id)
        if project is None:
            return None
        return PresentationProject(project=project)

    async def load_policy(self, version: str) -> CarouselPresentationPolicy:
        """Load the active presentation policy via the policy port."""
        return await self._require_policy().load_policy(version)

    async def validate_slides(self, project_id: str) -> SlideValidationReport:
        """Validate the project's slides via the slide-validation port."""
        return await self._require_slide_validation().validate_slides(project_id)

    def _require_policy(self) -> PresentationPolicyPort:
        port = self._ports.policy
        if port is None:
            raise RuntimeError(_ERR_NO_PORT.format(name="policy"))
        return port

    def _require_slide_validation(self) -> SlideValidationPort:
        port = self._ports.slide_validation
        if port is None:
            raise RuntimeError(_ERR_NO_PORT.format(name="slide_validation"))
        return port


# Message template for a use case invoked without its required port wired.
_ERR_NO_PORT = "presentation port not wired: {name}"


__all__ = [
    "PresentationPorts",
    "PresentationService",
]
