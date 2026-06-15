"""Outbound ports (Protocols) for the template module.

The domain/application layers depend on these Protocols; the infrastructure
layer provides implementations. This is the dependency-inversion seam wired
by ``bootstrap_module`` via manual constructor injection (ADR-0009 §9).

Per backend/CLAUDE.md, interfaces are ``typing.Protocol``, never ABCs.
"""

from __future__ import annotations

from typing import Protocol

from rag_backend.modules._template.domain.models import TemplateEntity


class TemplateRepository(Protocol):
    """Persistence port for the template aggregate.

    A real context declares the operations its application layer needs; the
    infrastructure adapter implements them against the actual store within
    the module's Unit-of-Work boundary.
    """

    async def get(self, entity_id: str) -> TemplateEntity | None:
        """Return the entity by id, or ``None`` if absent."""
        ...
