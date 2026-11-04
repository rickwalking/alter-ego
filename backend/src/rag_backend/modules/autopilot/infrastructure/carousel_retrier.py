"""Bind the Telegram "Tentar de novo" to the generation queue's owner Retry."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.carousel_retry import (
    CarouselRetryOutcome,
    CarouselRetryRequest,
)
from rag_backend.modules.editorial.public import EditorialWorkflowEngine
from rag_backend.modules.generation_queue.retry_public import (
    OwnerRetryCommand,
    RetrySurface,
    build_owner_retry,
)


class QueueCarouselRetrier:
    """Run the Retry on the webhook's session; the webhook commits."""

    def __init__(
        self,
        session: AsyncSession,
        engine_factory: Callable[[], EditorialWorkflowEngine],
    ) -> None:
        self._session = session
        self._engine_factory = engine_factory

    async def retry(self, request: CarouselRetryRequest) -> CarouselRetryOutcome:
        """Accepted with the phase being redone, or the refusal code."""
        service = build_owner_retry(
            self._session, self._engine_factory(), owns_transaction=False
        )
        result = await service.retry(
            OwnerRetryCommand(
                project_id=request.project_id,
                actor_id=request.actor_id,
                surface=RetrySurface.TELEGRAM,
            )
        )
        if result.accepted:
            return CarouselRetryOutcome(accepted=True, phase=result.phase)
        refusal = result.refusal.value if result.refusal is not None else ""
        return CarouselRetryOutcome(accepted=False, refusal=refusal)


__all__ = ["QueueCarouselRetrier"]
