"""Domain entities and value objects for the template module.

Private to the module. Illustrative only — no real business rules.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules._template.constants import STATUS_DRAFT


@dataclass(frozen=True)
class TemplateEntity:
    """An illustrative aggregate owned by this bounded context.

    A real context would model its aggregate (e.g. ``EditorialProject``,
    ``CarouselPresentation``) here, with invariants enforced in the domain.
    """

    entity_id: str
    title: str
    status: str = STATUS_DRAFT
