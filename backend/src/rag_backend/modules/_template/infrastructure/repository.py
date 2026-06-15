"""In-memory adapter implementing the template repository port.

Private to the module. Illustrative only — a real adapter would persist via
SQLAlchemy within the module's Unit-of-Work boundary. This implementation
satisfies the ``TemplateRepository`` Protocol structurally.
"""

from __future__ import annotations

from rag_backend.modules._template.domain.models import TemplateEntity


class InMemoryTemplateRepository:
    """A trivial repository adapter backed by a dict.

    Structurally implements ``TemplateRepository`` (no nominal inheritance —
    Protocols are satisfied by shape, per backend/CLAUDE.md).
    """

    def __init__(self) -> None:
        self._store: dict[str, TemplateEntity] = {}

    async def get(self, entity_id: str) -> TemplateEntity | None:
        """Return the entity by id, or ``None`` if absent."""
        return self._store.get(entity_id)
