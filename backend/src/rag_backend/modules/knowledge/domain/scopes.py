"""The document scopes an owner may choose, and the refusal for the others."""

from __future__ import annotations

from rag_backend.modules.knowledge.domain.models import DocumentScope

SELECTABLE_SCOPES: tuple[DocumentScope, ...] = (
    DocumentScope.PERSONAL,
    DocumentScope.PUBLIC,
)
"""The scopes an owner may choose for a document (the others are system scopes)."""

_SYSTEM_SCOPE = "Document in the {scope} scope cannot be moved"


class SystemScopeError(Exception):
    """A document in a system scope (carousel, internal) cannot change scope."""

    def __init__(self, scope: DocumentScope) -> None:
        """Name the system scope the document is in."""
        super().__init__(_SYSTEM_SCOPE.format(scope=scope.value))
        self.scope = scope
