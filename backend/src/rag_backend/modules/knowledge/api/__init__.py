"""Inbound-adapter layer for the knowledge bounded context (private).

Holds the boundary-safe view DTOs and is where HTTP/agent/worker inbound
adapters live once the routes move behind the facade (AE-0092/0093). Per
ADR-0009 §5-6, every inbound adapter creates the request-scoped Unit of Work at
this edge and supplies an ``ActorContext`` to the context-owned, deny-by-default
authorization policy before invoking the application service. This phase only
ships the view DTOs; the routes and policy arrive in AE-0092/0093.
"""

from rag_backend.modules.knowledge.api.views import (
    DocumentStatusView,
    KnowledgeDocumentView,
    SearchResultView,
)

__all__ = [
    "DocumentStatusView",
    "KnowledgeDocumentView",
    "SearchResultView",
]
