"""Application service (use case) for the editorial bounded context.

Private to the module. The public facade re-exports this type under its public
name; cross-module code never imports this path directly.

This is the **scaffolding** service for AE-0108: it wires to the re-exported
``CarouselRepository`` port via manual constructor injection (ADR-0009 §9) and
exposes a single read that returns the editorial aggregate. No routes/ACL are
moved here yet (AE-0109/0110); the editorial workflow behavior is unchanged.
"""

from __future__ import annotations

from uuid import UUID

from rag_backend.modules.editorial.domain.models import EditorialProject
from rag_backend.modules.editorial.domain.ports import CarouselRepository


class EditorialService:
    """Coordinates editorial use cases over a carousel project.

    Dependencies are injected through the constructor (manual constructor
    injection, ADR-0009 §9). The single transaction owner (Unit of Work) is
    supplied to the inbound edge via the module's bootstrap; later phases route
    write use cases through it.
    """

    def __init__(self, repository: CarouselRepository) -> None:
        self._repository = repository

    async def get_project(self, project_id: UUID) -> EditorialProject | None:
        """Return the editorial aggregate for a project, or ``None`` if absent."""
        project = await self._repository.get_project_by_id(project_id)
        if project is None:
            return None
        return EditorialProject(project=project)
