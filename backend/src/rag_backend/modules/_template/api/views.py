"""Public view DTOs exposed across the module boundary.

These are the boundary-safe shapes other modules and inbound adapters may
consume via the public facade. Internal domain entities are NOT exposed
directly — a view DTO decouples consumers from the module's internals.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateView:
    """Boundary-safe projection of the template aggregate.

    A real context returns view DTOs (or Pydantic response models at the HTTP
    edge) rather than leaking its domain entities to consumers.
    """

    entity_id: str
    title: str
    status: str
