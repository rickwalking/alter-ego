"""Public facade of the owner's carousel Retry (website and Telegram).

Kept apart from ``public.py`` so neither file exceeds the 400-line limit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rag_backend.modules.generation_queue.application.owner_retry import (
    OwnerRetryDependencies,
    OwnerRetryService,
)
from rag_backend.modules.generation_queue.domain.owner_retry import (
    OwnerRetryCommand,
    RetryKind,
    RetryRefusal,
    RetrySurface,
)
from rag_backend.modules.generation_queue.domain.owner_retry_ports import (
    RetryCapability,
    RetryResult,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from rag_backend.modules.editorial.public import EditorialWorkflowEngine


def build_owner_retry(
    session: AsyncSession,
    engine: EditorialWorkflowEngine,
    *,
    owns_transaction: bool = True,
) -> OwnerRetryService:
    """Compose the Retry on one session; the website owns the transaction."""
    from rag_backend.modules.generation_queue.infrastructure import (
        owner_retry_audit,
        owner_retry_store,
    )

    return OwnerRetryService(
        OwnerRetryDependencies(
            store=owner_retry_store.SqlOwnerRetryStore(session, engine),
            audit=owner_retry_audit.SqlOwnerRetryAudit(session),
        ),
        owns_transaction=owns_transaction,
    )


__all__ = [
    "OwnerRetryCommand",
    "OwnerRetryService",
    "RetryCapability",
    "RetryKind",
    "RetryRefusal",
    "RetryResult",
    "RetrySurface",
    "build_owner_retry",
]
