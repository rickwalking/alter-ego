"""Shared database/transaction plumbing for the Alter-Ego platform.

Holds cross-cutting persistence primitives shared by all bounded contexts —
currently the request-scoped Unit of Work that owns the transaction boundary
(ADR-0009 §9). No business or domain logic belongs here; only shared technical
infrastructure.

See ``docs/decisions/0009-adopt-domain-modular-monolith.md`` §9.
"""

from rag_backend.platform.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
    UnitOfWork,
)

__all__ = [
    "SqlAlchemyUnitOfWork",
    "UnitOfWork",
]
