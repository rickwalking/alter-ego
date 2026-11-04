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
    OwnerRetryService,
    RetryResult,
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
        self._started: list[tuple[RetryResult, str]] = []
        self._service: OwnerRetryService | None = None

    async def retry(self, request: CarouselRetryRequest) -> CarouselRetryOutcome:
        """Accepted with the phase being redone, or the refusal code."""
        result = await self._retry_service().retry(
            OwnerRetryCommand(
                project_id=request.project_id,
                actor_id=request.actor_id,
                surface=RetrySurface.TELEGRAM,
            )
        )
        if result.accepted:
            self._started.append((result, request.project_id))
            return CarouselRetryOutcome(accepted=True, phase=result.phase)
        refusal = result.refusal.value if result.refusal is not None else ""
        return CarouselRetryOutcome(accepted=False, refusal=refusal)

    async def deliver(self) -> None:
        """Announce each accepted run start; the webhook has committed."""
        started, self._started = self._started, []
        for result, project_id in started:
            await self._retry_service().announce(result, project_id)

    def discard(self) -> None:
        """Forget the run starts of a rolled-back webhook transaction."""
        self._started = []

    def _retry_service(self) -> OwnerRetryService:
        if self._service is None:
            self._service = build_owner_retry(
                self._session, self._engine_factory(), owns_transaction=False
            )
        return self._service


__all__ = ["QueueCarouselRetrier"]
