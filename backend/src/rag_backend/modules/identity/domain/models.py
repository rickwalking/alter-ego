"""Domain entities and value objects for the identity bounded context.

AE-0098 is a **behavior-preserving** extraction (ADR-0009). The identity
aggregate (``User``) and its role value object (``UserRole``) continue to live
at their legacy location ``rag_backend.domain.models.user`` so the existing
callers (the container, routes, dependencies, JWT helpers) keep importing the
exact same objects. This module **re-exports** them under the module's domain
namespace.

Physical relocation of these entities into the module is deferred to a later
phase. Until then ``User``/``UserRole`` are the same class objects as the legacy
ones (re-exports, not wrappers), so identity/isinstance checks and the existing
persistence adapters keep working unchanged.
"""

from __future__ import annotations

from rag_backend.domain.models.user import User, UserRole

__all__ = [
    "User",
    "UserRole",
]
