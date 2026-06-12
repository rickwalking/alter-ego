"""Application service (use case) for the template module.

Private to the module. The public facade re-exports this type under its
public name; cross-module code never imports this path directly.

Illustrative only — the read method returns a public view DTO and performs
no real work.
"""

from __future__ import annotations

from rag_backend.modules._template.api.views import TemplateView
from rag_backend.modules._template.domain.ports import TemplateRepository


class TemplateService:
    """Coordinates a use case for the template bounded context.

    Dependencies are injected through the constructor (manual constructor
    injection, ADR-0009 §9). A real service would also receive a Unit of
    Work so it can commit aggregate changes atomically within the module's
    boundary.
    """

    def __init__(self, repository: TemplateRepository) -> None:
        self._repository = repository

    async def get_view(self, entity_id: str) -> TemplateView | None:
        """Return a public view of the entity, or ``None`` if absent."""
        entity = await self._repository.get(entity_id)
        if entity is None:
            return None
        return TemplateView(
            entity_id=entity.entity_id,
            title=entity.title,
            status=entity.status,
        )
