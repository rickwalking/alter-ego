"""Inbound-adapter layer for the identity bounded context (private).

Holds the boundary-safe view DTOs and is where the HTTP inbound adapters live
once the routes move behind the facade (AE-0099). Per ADR-0009 §5-6, every
inbound adapter creates the request-scoped Unit of Work at this edge and
supplies an ``ActorContext`` to the context-owned, deny-by-default authorization
policy before invoking the application service. This phase only ships the view
DTOs; the routes move in AE-0099. The shared role-check dependencies
(``require_authenticated_user`` etc.) stay backed by ``api/middleware/auth.py``
at root and are re-exported through the module facade.
"""

from rag_backend.modules.identity.api.views import (
    AccessTokenView,
    UserListView,
    UserView,
)

__all__ = [
    "AccessTokenView",
    "UserListView",
    "UserView",
]
